# Weight of Evidence

**Full course playlist:**
[Artificial Intelligence & Machine Learning in Finance](https://www.youtube.com/playlist?list=PL4i4aZbplv9KZzkgz2U3RYObCcmXSHwOc)

**This module:**
[Lecture 6 - German Credit Data Part 2](https://www.youtube.com/watch?v=378jblUfpHU&list=PL4i4aZbplv9KZzkgz2U3RYObCcmXSHwOc&index=6)


---

Weight of Evidence (WOE) encodes the relationship of a categorical predictor variable with a binary target variable.  It orinated in the finace industry to help seperate the "good" from the "bad" ricks (loan default). 

WOE := Log ( numberOfNonEvents(Good) / numberOfEvents(Bad) )

where event means a default

Ratios of non events to events close to 1 indicate that the it has no predictive power

WOE is calcuated in different groups that are formed based on covariate of interest

For categorical variables these might be the categories of a pooling of multiple (smaller) subcategories.

For contineus variable one should create bins based on thresholds

Each catagory / bin should contain at least 5% of the all observations to avoid results to be driving to noise.



