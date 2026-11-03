---
module: ml-engineering
capability: Machine learning training, evaluation and deployment hygiene
technologies: ml
applies: machine learning, training, model, dataset, pytorch, sklearn, evaluation
checked_against: scikit-learn 1.5 and PyTorch 2.x documentation
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## data-leakage: Split before preprocessing to prevent data leakage
tags: ml, data leakage, train test split, preprocessing, pipeline, cross validation, evaluation
keywords: great validation score fails in production
refs: https://scikit-learn.org/stable/common_pitfalls.html#data-leakage

Fitting scalers, imputers, encoders or feature selection on the full dataset leaks test information into training. Split first, fit preprocessing on the training fold only (a scikit-learn `Pipeline` inside cross-validation does this), split time series by time, and group related rows (same user) into the same split.

## reproducible-training: Make training runs reproducible and tracked
tags: ml, reproducibility, random seed, experiment tracking, determinism, versioning
keywords: cannot reproduce results
refs: https://pytorch.org/docs/stable/notes/randomness.html

Seed every random source (Python, NumPy, framework), record library versions, data snapshot hash, configuration and metrics for every run in an experiment tracker, and note that some GPU operations are nondeterministic unless deterministic algorithms are enabled.

## right-metrics: Choose metrics that match the decision and the class balance
tags: ml, evaluation, metrics, precision, recall, imbalanced data, auc, calibration
keywords: 99 percent accuracy useless
refs: https://scikit-learn.org/stable/modules/model_evaluation.html

Accuracy misleads on imbalanced data. Use precision/recall, PR-AUC, or cost-weighted metrics that reflect what errors cost, choose the decision threshold on validation data, check calibration when probabilities are used, and report metrics per important segment, not only overall.

## eval-mode-and-no-grad: Switch to eval mode and disable gradients for inference
tags: ml, pytorch, inference, model eval, no_grad, inference_mode, dropout, batchnorm
keywords: predictions differ between runs, memory grows at inference
refs: https://pytorch.org/docs/stable/generated/torch.nn.Module.html#torch.nn.Module.eval

Call `model.eval()` before validation and inference so dropout and batch-norm behave deterministically, wrap inference in `torch.inference_mode()` (or `no_grad()`) to avoid building autograd graphs, and switch back with `model.train()` for training.

## training-serving-skew: Share feature code between training and serving
tags: ml, training serving skew, feature engineering, deployment, feature store, monitoring
keywords: model worse in production than offline
refs: https://developers.google.com/machine-learning/guides/rules-of-ml#training-serving_skew

Reimplementing features separately for serving produces subtle differences. Package preprocessing with the model (pipeline objects, exported graphs) or use a shared feature library/store, log served features, and compare their distributions to training data to detect skew and drift.

## gpu-data-pipeline: Keep the GPU fed: efficient data loading and mixed precision
tags: ml, gpu utilization, dataloader, num_workers, pin_memory, mixed precision, training speed
keywords: gpu at 30 percent utilization
refs: https://pytorch.org/tutorials/recipes/recipes/tuning_guide.html

Low GPU utilization is usually an input bottleneck. Use `DataLoader(num_workers>0, pin_memory=True, persistent_workers=True)`, preprocess offline where possible, use automatic mixed precision (`torch.autocast`) on supported hardware, and profile before buying more GPUs.
