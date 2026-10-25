"""Fit our own spectral classifier on expert-edited reference labels.

Geographic/event separation is fixed before evaluation. No pixel-random test split.
"""
from __future__ import annotations
import json
from pathlib import Path
import platform
import joblib
import numpy as np
import sklearn
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, precision_score, recall_score, jaccard_score, brier_score_loss, average_precision_score
from threadpoolctl import threadpool_limits
from features import spectral_features, SPECTRAL_NAMES

ROOT=Path(__file__).resolve().parent
ART=ROOT/"artifacts"
TEST_EVENTS=["Bolivia","USA"]
CALIBRATION_EVENTS=["Paraguay"]
SELECTION_EVENTS=["Spain"]


def logit(p):
    p=np.clip(p,1e-5,1-1e-5)
    return np.log(p/(1-p)).reshape(-1,1)


def calibrated_predict(bundle,X):
    with threadpool_limits(limits=2):
        raw=bundle["estimator"].predict_proba(X)[:,1]
        return bundle["calibrator"].predict_proba(logit(raw))[:,1].astype("float32")


def scores(y,p,threshold=.5):
    pred=p>=threshold
    bins=np.linspace(0,1,11);ece=0.
    reliability=[]
    for i in range(10):
        mask=(p>=bins[i]) & ((p<bins[i+1]) if i<9 else (p<=1))
        if not mask.any():continue
        predicted=float(p[mask].mean());actual=float(y[mask].mean())
        ece+=mask.mean()*abs(predicted-actual)
        reliability.append({"count":int(mask.sum()),"predicted":predicted,"observed":actual})
    return {"n":len(y),"water_fraction":float(y.mean()),"f1":float(f1_score(y,pred,zero_division=0)),
            "precision":float(precision_score(y,pred,zero_division=0)),"recall":float(recall_score(y,pred,zero_division=0)),
            "iou":float(jaccard_score(y,pred,zero_division=0)),"brier":float(brier_score_loss(y,p)),
            "average_precision":float(average_precision_score(y,p)) if y.any() else None,"ece_10":float(ece),"reliability":reliability}


def main():
    with np.load(ART/"reference_samples.npz") as z:
        raw=z["X"];y=z["y"].astype("uint8");events=z["event"];chips=z["chip"]
    X=spectral_features(raw)
    test=np.isin(events,TEST_EVENTS);cal=np.isin(events,CALIBRATION_EVENTS);selection=np.isin(events,SELECTION_EVENTS)
    train=~(test|cal|selection)
    if min(train.sum(),test.sum(),cal.sum(),selection.sum())<100:
        raise ValueError("Insufficient data in fixed event-separated partitions")
    # Equal total fitting weight per chip; preserve the class prevalence within it.
    _,inverse,counts=np.unique(chips[train],return_inverse=True,return_counts=True)
    weights=1/counts[inverse];weights*=len(weights)/weights.sum()
    candidates={
        "hist_gradient_boosting":HistGradientBoostingClassifier(max_iter=180,max_leaf_nodes=23,min_samples_leaf=35,learning_rate=.07,l2_regularization=1.,early_stopping=False,random_state=42),
        "extra_trees":ExtraTreesClassifier(n_estimators=100,max_depth=17,min_samples_leaf=12,max_features=.8,n_jobs=2,random_state=42),
    }
    selection_results={};bundles={}
    for name,model in candidates.items():
        print("Fitting",name,"on",int(train.sum()),"pixels from",sorted(set(events[train])),flush=True)
        with threadpool_limits(limits=2):model.fit(X[train],y[train],sample_weight=weights)
        calibrator=LogisticRegression(C=1,solver="lbfgs",max_iter=500)
        with threadpool_limits(limits=2):calibrator.fit(logit(model.predict_proba(X[cal])[:,1]),y[cal])
        bundle={"estimator":model,"calibrator":calibrator,"features":SPECTRAL_NAMES}
        p=calibrated_predict(bundle,X[selection])
        threshold=max(np.arange(.2,.81,.025),key=lambda t:f1_score(y[selection],p>=t,zero_division=0))
        bundle["threshold"]=float(threshold)
        selection_results[name]={"threshold":float(threshold),**scores(y[selection],p,threshold)}
        bundles[name]=bundle
        print("Selection",name,selection_results[name]["f1"],flush=True)
    chosen=max(selection_results,key=lambda k:selection_results[k]["f1"])
    bundle=bundles[chosen]
    # This is the first and only use of the held-out test labels in this training run.
    p=calibrated_predict(bundle,X[test]);test_y=y[test];test_e=events[test]
    mndwi=X[test,SPECTRAL_NAMES.index("MNDWI")]
    m_selection=X[selection,SPECTRAL_NAMES.index("MNDWI")]
    tuned_mndwi=float(max(np.arange(-.3,.61,.025),key=lambda t:f1_score(y[selection],m_selection>=t,zero_division=0)))
    binary=lambda a:np.asarray(a,dtype="float32")
    report={"version":"2.0","task":"Surface water classification, not flood persistence or business interruption", "selected_model":chosen,"features":SPECTRAL_NAMES,
            "partitions":{"train_events":sorted(set(events[train])),"calibration_events":CALIBRATION_EVENTS,"selection_events":SELECTION_EVENTS,"untouched_test_events":TEST_EVENTS,
                          "train_pixels":int(train.sum()),"calibration_pixels":int(cal.sum()),"selection_pixels":int(selection.sum()),"test_pixels":int(test.sum())},
            "selection_results":selection_results,"decision_threshold":bundle["threshold"],"tuned_mndwi_threshold":tuned_mndwi,
            "test":{"learned":scores(test_y,p,bundle["threshold"]),"mndwi_fixed_015":scores(test_y,binary(mndwi>.15)),"mndwi_validation_tuned":scores(test_y,binary(mndwi>=tuned_mndwi))},
            "test_by_event":{},"limitations":["Expert-edited labels initialized from an optical index; residual annotation bias is possible.","Subset of reference chips; not a full official Sen1Floods11 benchmark.","Calibration is tested geographically but is not guaranteed in Brazil.","Water classification accuracy does not establish flood-prediction or trading performance."],
            "runtime":{"python":platform.python_version(),"sklearn":sklearn.__version__},"random_seed":42}
    for event in sorted(set(test_e)):
        mask=test_e==event
        report["test_by_event"][event]={"learned":scores(test_y[mask],p[mask],bundle["threshold"]),
                                       "mndwi_fixed_015":scores(test_y[mask],binary(mndwi[mask]>.15)),
                                       "mndwi_validation_tuned":scores(test_y[mask],binary(mndwi[mask]>=tuned_mndwi))}
    confident=(p<.2)|(p>.8)
    report["selective_test"]={"coverage":float(confident.mean()),"scores":scores(test_y[confident],p[confident],bundle["threshold"])}
    bundle["selected_model"]=chosen;bundle["training_version"]="2.0";bundle["test_events"]=TEST_EVENTS
    joblib.dump(bundle,ART/"water_classifier.joblib",compress=3)
    (ART/"classifier_report.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print(json.dumps({"model":chosen,"test_f1":report["test"]["learned"]["f1"],"baseline_f1":report["test"]["mndwi_fixed_015"]["f1"],"tuned_baseline_f1":report["test"]["mndwi_validation_tuned"]["f1"]},indent=2),flush=True)


if __name__=="__main__":main()
