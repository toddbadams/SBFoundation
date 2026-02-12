# Simple Linear Regression

**Full course playlist:**
[Artificial Intelligence & Machine Learning in Finance](https://www.youtube.com/playlist?list=PL4i4aZbplv9KZzkgz2U3RYObCcmXSHwOc)

**This module:**
[Lecture 8 - Simple Linear Regression](https://www.youtube.com/watch?v=unCI7a1owQo&list=PL4i4aZbplv9KZzkgz2U3RYObCcmXSHwOc)


Below are **course-work level notes** on **Supervised vs. Unsupervised Learning**, written in a **clear, exam-ready academic style** suitable for university assignments, revision, or lecture notes.

---

# Supervised vs. Unsupervised Learning

## 1. Introduction

Machine Learning (ML) algorithms are commonly classified based on the **type of feedback available during learning**.
The two most fundamental categories are:

* **Supervised learning**
* **Unsupervised learning**

The key distinction lies in **whether labeled output data is available** during training.

---

## 2. Supervised Learning

### 2.1 Definition

**Supervised learning** refers to algorithms that learn a mapping from **input variables (features)** to a **known output variable (label)** using labeled training data.

Formally, given:

* Input features ( X = (x_1, x_2, ..., x_n) )
* Output labels ( Y )

The goal is to learn a function:
$$ 
f(X) \rightarrow Y 
$$

---

### 2.2 Characteristics

* Requires **labeled training data**
* Learns by minimizing prediction error
* Performance can be quantitatively evaluated
* Strongly dependent on data quality and labeling accuracy

---

### 2.3 Types of Supervised Learning

#### 2.3.1 Classification

* Output variable is **categorical**
* Goal: assign inputs to predefined classes

**Examples**

* Email spam detection (spam / not spam)
* Medical diagnosis (disease / no disease)

**Common Algorithms**

* Logistic Regression
* Decision Trees
* Random Forests
* Support Vector Machines (SVM)
* k-Nearest Neighbors (k-NN)
* Neural Networks

---

#### 2.3.2 Regression

* Output variable is **continuous**
* Goal: predict numerical values

**Examples**

* Stock price prediction
* House price estimation

**Common Algorithms**

* Linear Regression
* Polynomial Regression
* Ridge / Lasso Regression
* Support Vector Regression (SVR)
* Neural Networks

**Simple Linear Regression** models the relationship between:
* **One independent variable** (X)
* **One dependent variable** (Y)

The relationship is assumed to be **linear**.

$$
Y = \beta_0 + \beta_1 X + \varepsilon
$$

Where:
$$\beta_0  = intercept (value of (Y) when (X = 0))$$
* ( $$\beta_1 $$) = slope (change in (Y) for a one-unit change in (X))
* ( $$\varepsilon $$) = random error term

Estimate ( \beta_0 ) and ( \beta_1 ) such that the **sum of squared errors** is minimized:

$$
\min \sum (Y_i - \hat{Y}_i)^2
$$

This method is called **Ordinary Least Squares (OLS)**.

**Assumptions**
1. **Linearity** – relationship between (X) and (Y) is linear
2. **Independence** – observations are independent
3. **Homoscedasticity** – constant variance of errors
4. **Normality of errors** – residuals are normally distributed

**Interpretation**
* **Slope ((\beta_1))**: expected change in (Y) per unit increase in (X)
* **Intercept ((\beta_0))**: expected value of (Y) when (X = 0)

**Model Evaluation**

Common metrics:
* **(R^2)** – proportion of variance in (Y) explained by (X)
* **Mean Squared Error (MSE)**
* **Residual plots** for assumption checking

**Applications**
* Trend analysis
* Forecasting
* Quantifying relationships between variables

**Limitations**
* Only captures **linear relationships**
* Sensitive to **outliers**
* Poor performance if assumptions are violated


### 2.4 Evaluation Metrics

Because true labels are known, supervised learning can be evaluated using objective metrics:

**Classification Metrics**

* Accuracy
* Precision, Recall, F1-score
* ROC-AUC

**Regression Metrics**

* Mean Squared Error (MSE)
* Root Mean Squared Error (RMSE)
* Mean Absolute Error (MAE)
* (R^2) score

---

### 2.5 Advantages and Limitations

**Advantages**

* High predictive accuracy when sufficient labeled data is available
* Clear evaluation criteria
* Well understood theoretically

**Limitations**

* Requires large labeled datasets (often expensive)
* Risk of overfitting
* Performance degrades with noisy or biased labels

---

## 3. Unsupervised Learning

### 3.1 Definition

**Unsupervised learning** refers to algorithms that analyze data **without labeled outputs** in order to discover hidden patterns or structures.

Given:

* Input data ( X = (x_1, x_2, ..., x_n) )

The goal is to uncover:

* Groupings
* Latent structures
* Feature relationships

---

### 3.2 Characteristics

* No labeled data required
* Focuses on pattern discovery
* Results are often exploratory
* Evaluation is more subjective

---

### 3.3 Types of Unsupervised Learning

#### 3.3.1 Clustering

* Groups similar data points together
* No predefined class labels

**Examples**

* Customer segmentation
* Image grouping

**Common Algorithms**

* k-Means
* Hierarchical Clustering
* DBSCAN
* Gaussian Mixture Models (GMM)

---

#### 3.3.2 Dimensionality Reduction

* Reduces number of features
* Preserves important structure or variance

**Examples**

* Data visualization
* Noise reduction

**Common Algorithms**

* Principal Component Analysis (PCA)
* Singular Value Decomposition (SVD)
* Autoencoders
* t-SNE (visualization)

---

#### 3.3.3 Association Rule Mining

* Discovers relationships between variables
* Often used in transactional data

**Examples**

* Market basket analysis

**Common Algorithms**

* Apriori
* FP-Growth

---

### 3.4 Evaluation Methods

Evaluation is more challenging due to lack of labels.

**Common Approaches**

* Internal metrics (e.g. silhouette score for clustering)
* Stability analysis
* Domain expert validation
* Downstream task performance

---

### 3.5 Advantages and Limitations

**Advantages**

* No labeling cost
* Useful for exploratory data analysis
* Can reveal unexpected patterns

**Limitations**

* Hard to validate results
* Sensitive to parameter choices
* Interpretability can be challenging

---

## 4. Key Differences Between Supervised and Unsupervised Learning

| Aspect        | Supervised Learning        | Unsupervised Learning                |
| ------------- | -------------------------- | ------------------------------------ |
| Data          | Labeled                    | Unlabeled                            |
| Goal          | Prediction                 | Pattern discovery                    |
| Output        | Known during training      | Unknown                              |
| Evaluation    | Objective metrics          | Often subjective                     |
| Typical Tasks | Classification, Regression | Clustering, Dimensionality Reduction |
| Data Cost     | High (labeling)            | Lower                                |

---

## 5. Hybrid and Related Approaches

### 5.1 Semi-Supervised Learning

* Combines small labeled dataset with large unlabeled dataset
* Useful when labeling is expensive

### 5.2 Self-Supervised Learning

* Labels are generated automatically from the data
* Common in deep learning (e.g. contrastive learning)

---

## 6. When to Use Each Approach

**Use Supervised Learning when:**

* Labeled data is available
* Predictive accuracy is critical
* Clear evaluation is required

**Use Unsupervised Learning when:**

* Data is unlabeled
* Goal is exploration or structure discovery
* Feature engineering or data understanding is needed

---

## 7. Summary

* Supervised learning learns from **examples with known answers**
* Unsupervised learning discovers **hidden structure without answers**
* Both are foundational to modern data science
* Choice depends on **data availability, problem type, and objectives**

