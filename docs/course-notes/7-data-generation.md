# Data Generation

**Full course playlist:**
[Artificial Intelligence & Machine Learning in Finance](https://www.youtube.com/playlist?list=PL4i4aZbplv9KZzkgz2U3RYObCcmXSHwOc)

**This module:**
[Lecture 7 - Data Generation](https://www.youtube.com/watch?v=UwWuElTdXpI&list=PL4i4aZbplv9KZzkgz2U3RYObCcmXSHwOc)

Many ML technics rely on synthetic data for training and testing

Synthetic data is artifical data created by algoriths that mirror statiscial properties of the source data while not revealing private data

Main purpose of synthetic data is preserving privacy and creating training and test data

Many training data sets are highly imbalanced making classification tasks difficult. Synthetic data can restore the balance.


## Privacy-Preserving Data Mining
[Utility-Based Anonymization Using Generalization Boundaries to Protect Sensitive Attributes](https://www.scirp.org/reference/referencespapers?referenceid=1496242)

### 1. Introduction

Privacy-preserving data mining (PPDM) addresses the conflict between:

* **The utility of data mining**, and
* **The protection of sensitive individual or organizational data**

With the widespread availability of electronic data, traditional anonymization (e.g. removing names) is insufficient because **individuals can often be re-identified using combinations of attributes** (quasi-identifiers).

**Key challenge**

> Preserve useful data mining results while preventing disclosure of sensitive information.

**Core trade-off**

* Increased privacy ⇒ reduced data accuracy / utility
* Increased utility ⇒ greater privacy risk

---

### 2. Major Categories of Privacy-Preserving Techniques

The survey identifies **four broad classes** of PPDM techniques:

1. **Randomization (Perturbation-based methods)**
2. **Group-based anonymization (k-anonymity family)**
3. **Distributed privacy-preserving data mining**
4. **Privacy preservation of application outputs**

---

### 3. Randomization (Perturbation-Based Methods)

#### 3.1 Basic Idea

Noise is added to each data record independently:

  [ Z = X + Y ]

  where:
  * (X) = original data
  * (Y) = random noise
  * (Z) = released data

* Individual records cannot be reconstructed
* Aggregate statistical properties can be estimated

---

#### 3.2 Key Properties

**Advantages**

* Simple to implement
* Can be applied at data collection time
* No trusted central server required

**Limitations**

* Outliers are weakly protected
* Susceptible to **reconstruction attacks**
* Effectiveness declines sharply in **high dimensions**

---

#### 3.3 Privacy Quantification

Early measures (e.g. confidence intervals) are insufficient because:

Attackers can use **background knowledge** and reconstructed distributions

**Improved metric**

* Based on **information theory**
* Uses **differential entropy** and **mutual information**

Key measures:

* Privacy of a variable (A):
  [ \Pi(A) = 2^{h(A)} ]
* Privacy loss when revealing (B):
  [ P(A|B) = 1 - 2^{-I(A;B)} ]

This formalism captures **how much uncertainty is reduced** when perturbed data is released.

---

#### 3.4 Adversarial Attacks

Two major attack classes:

1. **Correlation-based attacks**
   * PCA / spectral filtering can remove noise
2. **Public information attacks**
   * Matching perturbed records against known external datasets

These attacks become more effective as **dimensionality increases**.

---

#### 3.5 Variants of Randomization

* **Multiplicative perturbation**
  * Preserves distances approximately
  * Useful for clustering and classification
* **Data swapping**
  * Preserves marginal distributions
  * Can be combined with k-anonymity
* **Streaming data perturbation**
  * Correlation-aware noise improves robustness

---

### 4. Group-Based Anonymization

#### 4.1 k-Anonymity

**Definition**

> A dataset satisfies k-anonymity if each record is indistinguishable from at least (k-1) other records with respect to quasi-identifiers.

**Techniques**

* Generalization (e.g. age → age range)
* Suppression (removing values entirely)

---

#### 4.2 Algorithms for k-Anonymity

Key approaches include:

* **Top-down specialization**
* **Bottom-up generalization**
* **Clustering-based anonymization**
* **Search-based heuristics**
* **Approximation algorithms** with theoretical guarantees

**Complexity**

* Optimal k-anonymization is **NP-hard**
* Practical systems rely on heuristics or approximations

---

#### 4.3 Weaknesses of k-Anonymity

* **Homogeneity attack**
  * All sensitive values in a group are identical
* **Background knowledge attack**
  * External knowledge narrows possible sensitive values

---

### 5. Extensions of k-Anonymity

#### 5.1 l-Diversity

**Goal**
* Ensure diversity of sensitive attributes within each group

**Definition**
> Each equivalence class must contain at least (l) well-represented sensitive values.

**Limitation**
* Still vulnerable with skewed data distributions
* Suffers from the curse of dimensionality

---

#### 5.2 t-Closeness

**Key idea**
* Distribution of sensitive attributes in each group should be close to the global distribution

**Metric**
* Earth Mover’s Distance (EMD)

**Strength**
* Addresses skewness and semantic sensitivity
* More robust than l-diversity for numeric data

---

#### 5.3 Personalized Privacy

* Different users may require different privacy levels
* Anonymity constraints vary per record
* Often implemented via **condensation and synthetic data generation**

---

### 6. Utility-Based Privacy Preservation

Privacy transformations reduce data usefulness.

**Goal**
> Maximize utility subject to privacy constraints.

Techniques include:
* Utility-aware generalization
* Local recoding
* Workload-aware anonymization
* Application-specific anonymization (e.g. classification-aware)

---

### 7. Distributed Privacy-Preserving Data Mining

#### 7.1 Problem Setting
* Data distributed across multiple parties
* Parties do not trust each other
* Want global results without sharing raw data

---

#### 7.2 Secure Multi-Party Computation (SMC)
* Cryptographic protocols compute functions without revealing inputs
* Uses primitives like:

  * Secure sum
  * Secure dot product
  * Oblivious transfer

**Adversary models**
* Semi-honest
* Malicious

---

#### 7.3 Data Partitioning

* **Horizontally partitioned**: different records, same attributes
* **Vertically partitioned**: same records, different attributes

Algorithms exist for:

* Classification
* Clustering
* Association rule mining
* Collaborative filtering

---

### 8. Privacy of Application Outputs

Even sanitized data can leak privacy through outputs.

### 8.1 Association Rule Hiding

* **Distortion**: flip values
* **Blocking**: replace values with unknowns

Side effects:
* Loss of non-sensitive rules
* Creation of spurious rules

---

#### 8.2 Classifier Downgrading

* Reduce classification accuracy deliberately
* Preserve utility for non-sensitive tasks

---

#### 8.3 Query Auditing and Inference Control

Two approaches:

* **Deny dangerous queries**
* **Perturb query results**

Related to:

* Differential privacy
* Noise calibrated to query sensitivity

---

### 9. Curse of Dimensionality

A fundamental limitation across all methods:

* High dimensional data + background knowledge ⇒ re-identification becomes likely
* Requires heavy generalization or suppression
* Results in major utility loss

**Key insight**

> Perfect privacy with high utility is often impossible in high dimensions.

---

### 10. Applications

* Medical data (Scrub, Datafly systems)
* Bioterrorism surveillance
* Homeland security
* Video and facial anonymization
* Genomic privacy

---

### 11. Summary

* Privacy-preserving data mining is a **trade-off problem**
* No single technique is universally optimal
* Effectiveness depends on:

  * Data type
  * Dimensionality
  * Adversary knowledge
  * Intended application
* High-dimensional data poses fundamental limits


