"""Train next-observation water forecasting on 2023; May 2024 stays held out.

Targets are proxy labels from a frozen, externally trained water classifier.
They are not independently observed business interruptions or field measurements.
"""
from __future__ import annotations
from datetime import datetime
import json
from pathlib import Path
import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import f1_score
from threadpoolctl import threadpool_limits
from features import TEMPORAL_NAMES
from temporal import TimeSeries
from train_classifier import scores

ROOT=Path(__file__).resolve().parent
ART=ROOT/"artifacts"


def pairs(dates, lower, upper):
    result=[]
    for current in dates:
        if current<lower or current>upper:continue
        start=datetime.fromisoformat(current)
        candidates=[d for d in dates if 10<=(datetime.fromisoformat(d)-start).days<=20 and d<=upper]
        if candidates:
            target=min(candidates,key=lambda d:abs((datetime.fromisoformat(d)-start).days-15))
            result.append((current,target))
    return result


def sample_pair(ts,issue,target,rng,n=12000):
    lead=(datetime.fromisoformat(target)-datetime.fromisoformat(issue)).days
    c=ts.context(issue,lead)
    target_p,target_valid=ts.observation(target)
    # Focus on flood-prone changes, excluding normal water known at issue time.
    valid=c["valid"] & target_valid & (c["normal"]<ts.threshold)
    ids=np.flatnonzero(valid)
    if len(ids)<100:return None
    ids=rng.choice(ids,min(n,len(ids)),replace=False)
    X=c["X"].reshape(-1,len(TEMPORAL_NAMES))[ids]
    y=(target_p.ravel()[ids]>=ts.threshold).astype("uint8")
    return X,y,{"issue":issue,"target":target,"lead_days":lead,"n":len(ids),"positive_fraction":float(y.mean()),"history_dates":c["history_dates"]}


def main():
    ts=TimeSeries();ts.prepare_probabilities()
    rng=np.random.default_rng(42)
    specs={"train":pairs(ts.dates,"2023-01-01","2023-10-31"),"validation":pairs(ts.dates,"2023-11-01","2024-03-31")}
    samples={};metadata={}
    for split,ps in specs.items():
        records=[sample_pair(ts,a,b,rng) for a,b in ps];records=[r for r in records if r is not None]
        if len(records)<2:raise ValueError("Insufficient historical pairs for "+split)
        samples[split]=(np.concatenate([r[0] for r in records]),np.concatenate([r[1] for r in records]))
        metadata[split]=[r[2] for r in records]
    X,y=samples["train"];VX,VY=samples["validation"]
    model=HistGradientBoostingClassifier(max_iter=160,max_leaf_nodes=15,learning_rate=.06,min_samples_leaf=80,l2_regularization=5,early_stopping=False,random_state=42)
    print("FORECAST TRAIN",len(y),"pixels",len(metadata["train"]),"pairs",flush=True)
    # Equal total weight for each acquisition pair.
    weights=np.concatenate([np.full(r["n"],1/r["n"]) for r in metadata["train"]]);weights*=len(weights)/weights.sum()
    with threadpool_limits(limits=2):
        model.fit(X,y,sample_weight=weights)
        vp=model.predict_proba(VX)[:,1]
    # Fixed candidate family; all blend weights and thresholds selected on historical validation only.
    options=[]
    for alpha in [0.,.25,.5,.75,1.]:
        combined=(1-alpha)*VX[:,0]+alpha*vp
        cut=ts.threshold if alpha==0 else float(max(np.arange(.2,.91,.025),key=lambda t:f1_score(VY,combined>=t,zero_division=0)))
        options.append({"alpha":alpha,"threshold":cut,"scores":scores(VY,combined,cut)})
    chosen=max(options,key=lambda r:r["scores"]["f1"])
    alpha=chosen["alpha"];threshold=chosen["threshold"]
    validation_model=chosen["scores"]
    validation_persistence=scores(VY,VX[:,0],ts.threshold)
    use_learned=alpha>0
    bundle={"estimator":model,"threshold":threshold,"features":TEMPORAL_NAMES,"deployment":"learned" if use_learned else "persistence", "blend_alpha":alpha,
            "selection_basis":"Blend weight and threshold selected only on November 2023–March 2024 validation; final additional test is 2–22 June 2024", "trained_until":"2023-10-31"}
    joblib.dump(bundle,ART/"water_forecast.joblib",compress=3)
    # Save compact training data so fitting is reproducible without another download.
    np.savez_compressed(ART/"forecast_samples.npz",X=X,y=y,VX=VX,VY=VY)
    issue,target="2024-05-06","2024-05-21"
    c=ts.context(issue,15);tp,tv=ts.observation(target)
    valid=c["valid"]&tv&(c["normal"]<ts.threshold)
    with threadpool_limits(limits=2):
        prediction=model.predict_proba(c["X"].reshape(-1,len(TEMPORAL_NAMES)))[:,1].reshape(c["p"].shape).astype("float32")
    raw_prediction=prediction.copy()
    prediction=(1-alpha)*c["p"]+alpha*prediction
    actual=(tp[valid]>=ts.threshold).astype("uint8")
    model_test=scores(actual,prediction[valid],threshold)
    persistence_test=scores(actual,c["p"][valid],ts.threshold)
    # Spatial block metrics acknowledge that pixels are not independent events.
    blocks=[]
    h,w=valid.shape
    for i in range(0,h,128):
        for j in range(0,w,128):
            v=valid[i:i+128,j:j+128]
            if v.sum()<100:continue
            target_block=(tp[i:i+128,j:j+128][v]>=ts.threshold).astype("uint8")
            if not target_block.any():continue
            blocks.append({"row":i,"col":j,"learned_f1":scores(target_block,prediction[i:i+128,j:j+128][v],threshold)["f1"],
                           "persistence_f1":scores(target_block,c["p"][i:i+128,j:j+128][v],ts.threshold)["f1"]})
    deployed=prediction if use_learned else c["p"]
    np.savez_compressed(ART/"forecast_snapshot.npz",forecast_p=deployed,learned_p=prediction,raw_learned_p=raw_prediction,current_p=c["p"],normal_p=c["normal"],
                        history_frequency=c["frequency"],history_count=c["count"],valid=c["valid"])
    report={"version":"2.0","features":TEMPORAL_NAMES,"train_pairs":metadata["train"],"validation_pairs":metadata["validation"],
            "target":"Water at a later observation, as classified by a frozen external-reference-trained classifier", "target_type":"proxy labels, not independent flood ground truth", "horizon_training_range_days":[10,20],
            "validation":{"learned":validation_model,"persistence":validation_persistence,"candidates":options},"blend_alpha":alpha,"deployment":bundle["deployment"],"deployment_selection":bundle["selection_basis"],
            "threshold":threshold,"water_classification_threshold":ts.threshold,"heldout_test":{"status":"development_case_seen_in_initial_experiment; excluded from fitting and selection", "issue":issue,"target":target,"learned":model_test,"persistence":persistence_test,"valid_percent":float(valid.mean()*100),"spatial_blocks":blocks},
            "issue_history_dates":c["history_dates"],"limitations":["Temporal test is one flood event in the same region; no claim of geographic forecasting generalization.","Target water maps are proxy labels from the frozen classifier, not independent field observations.","No future weather, no future-frame interpolation; training uses only historical causal inputs.","No business-interruption or price labels are fitted."]}
    # Additional temporal pair fixed before this extended fitting run; evaluated once after model selection.
    final_issue,final_target="2024-06-02","2024-06-22"
    fc=ts.context(final_issue,20);fp,fv=ts.observation(final_target)
    eligible=fc["valid"]&fv&(fc["normal"]<ts.threshold)
    with threadpool_limits(limits=2):
        raw_final=model.predict_proba(fc["X"].reshape(-1,len(TEMPORAL_NAMES)))[:,1].reshape(fc["p"].shape)
    pred_final=(1-alpha)*fc["p"]+alpha*raw_final
    final_y=(fp[eligible]>=ts.threshold).astype("uint8")
    report["additional_temporal_test"]={"issue":final_issue,"target":final_target,"lead_days":20,
        "learned":scores(final_y,pred_final[eligible],threshold),"persistence":scores(final_y,fc["p"][eligible],ts.threshold),
        "limitations":"Same region and flood aftermath; not an independent geographic event. Proxy target water maps."}
    report["limitations"].append("May case was inspected in the initial two-pair experiment. It is a development case, not an untouched final test for the extended version.")
    # Engineering release gate: a validation winner is not promoted when it fails
    # the later check. Test labels never enter fitting or threshold selection.
    report["validation_selected_deployment"]=bundle["deployment"]
    release_passed=(model_test["f1"]>=persistence_test["f1"] and
                    report["additional_temporal_test"]["learned"]["f1"]>=report["additional_temporal_test"]["persistence"]["f1"])
    report["release_gate"]={"passed":release_passed,"policy":"Do not promote a temporal candidate that underperforms persistence on either later check; keep all candidate results visible.",
                            "note":"Later checks are used for release acceptance, not for refitting. No unbiased performance estimate for a newly selected trading strategy is claimed."}
    fractions=[];offset=0
    for pair in metadata["train"]:
        group=X[offset:offset+pair["n"]];offset+=pair["n"]
        fractions.append(float((group[:,0]>=ts.threshold).mean()))
    report["domain_diagnostics"]={"max_training_current_water_fraction":max(fractions),
        "may_current_water_fraction":float((c["p"][valid]>=ts.threshold).mean()),
        "june_current_water_fraction":float((fc["p"][eligible]>=ts.threshold).mean()),
        "interpretation":"Training is dominated by much smaller new-water extents; extraordinary flood extent can cause distribution shift."}
    if not release_passed:
        bundle["deployment"]="persistence"
        bundle["release_rejection"]="Temporal candidate failed later checks; not promoted."
        joblib.dump(bundle,ART/"water_forecast.joblib",compress=3)
        report["deployment"]="persistence"
        # Save the rejected candidate separately, while the default forecast is safe.
        np.savez_compressed(ART/"forecast_snapshot.npz",forecast_p=c["p"],learned_p=prediction,raw_learned_p=raw_prediction,
                            current_p=c["p"],normal_p=c["normal"],history_frequency=c["frequency"],history_count=c["count"],valid=c["valid"])
    (ART/"forecast_report.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print(json.dumps({"deployment":bundle["deployment"],"validation_f1_learned":validation_model["f1"],"validation_f1_persistence":validation_persistence["f1"],"test_f1_learned":model_test["f1"],"test_f1_persistence":persistence_test["f1"],"blend_alpha":alpha,"additional_test_learned":report["additional_temporal_test"]["learned"]["f1"],"additional_test_persistence":report["additional_temporal_test"]["persistence"]["f1"]},indent=2),flush=True)


if __name__=="__main__":main()
