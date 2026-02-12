# German Credit Data Example

## Importing the data


``` R
# Importing the data
germanCredit = read.table(
  "http://archive.ics.uci.edu/ml/machine-learning-databases/statlog/german/german.data"
)

dim(germanCredit) # [1] 1000 21   # 1000 observations of 21 variables

# Reduce number of features to make them fit on one slide,
# 21st feature is the response/target variable (credit rating: good/bad)
germanCredit <- germanCredit[, c(1:5, 21)]
```

This data consists of 1000 observations of 6 variables
The features are of type factor and type integer
Factors represent categorical or ordinal variables and have advantage of category labels are only stored once, requiring less RAM

The values of a factor are referred to as levels. The first vairable V1 has levels A11, A12, A13, A14 which are represented by integegers 1, 2, 4, 1, 

```
A11 6 A34 A43 1169 A65 A75 4 A93 A101 4 A121 67 A143 A152 2 A173 1 A192 A201 1
A12 48 A32 A43 5951 A61 A73 2 A92 A101 2 A121 22 A143 A152 1 A173 1 A191 A201 2
A14 12 A34 A46 2096 A61 A74 2 A93 A101 3 A121 49 A143 A152 1 A172 2 A191 A201 1
A11 42 A32 A42 7882 A61 A74 2 A93 A103 4 A122 45 A143 A153 1 A173 2 A191 A201 1
A11 24 A33 A40 4870 A61 A73 3 A93 A101 4 A124 53 A143 A153 2 A173 2 A191 A201 2
A14 36 A32 A46 9055 A65 A73 2 A93 A101 4 A124 35 A143 A153 1 A172 2 A192 A201 1
A14 24 A32 A42 2835 A63 A75 3 A93 A101 4 A122 53 A143 A152 1 A173 1 A191 A201 1
A12 36 A32 A41 6948 A61 A73 2 A93 A101 2 A123 35 A143 A151 1 A174 1 A192 A201 1
A14 12 A32 A43 3059 A64 A74 2 A91 A101 4 A121 61 A143 A152 1 A172 1 A191 A201 1
A12 30 A34 A40 5234 A61 A71 4 A94 A101 2 A123 28 A143 A152 2 A174 1 A191 A201 2
```

Variable names are not meaningful

The description of the variables:  https://archive.ics.uci.edu/ml/datasets/statlog+(german+credit+data)

```
Attribute 1:  (qualitative)      
    Status of existing checking account
    A11 :      ... <    0 DM
    A12 : 0 <= ... <  200 DM
    A13 :      ... >= 200 DM / salary assignments for at least 1 year
    A14 : no checking account

Attribute 2:  (numerical)
	Duration in month

Attribute 3:  (qualitative)
	Credit history
	A30 : no credits taken/ all credits paid back duly
    A31 : all credits at this bank paid back duly
	A32 : existing credits paid back duly till now
    A33 : delay in paying off in the past
	A34 : critical account/  other credits existing (not at this bank)

Attribute 4:  (qualitative)
	Purpose
	A40 : car (new)
	A41 : car (used)
	A42 : furniture/equipment
	A43 : radio/television
	A44 : domestic appliances
	A45 : repairs
	A46 : education
	A47 : (vacation - does not exist?)
	A48 : retraining
	A49 : business
	A410 : others

Attribute 5:  (numerical)
	Credit amount

Attibute 6:  (qualitative)
	Savings account/bonds
	A61 :          ... <  100 DM
	A62 :   100 <= ... <  500 DM
	A63 :   500 <= ... < 1000 DM
	A64 :          .. >= 1000 DM
    A65 :   unknown/ no savings account

Attribute 7:  (qualitative)
	Present employment since
	A71 : unemployed
	A72 :       ... < 1 year
	A73 : 1  <= ... < 4 years  
	A74 : 4  <= ... < 7 years
	A75 :       .. >= 7 years

Attribute 8:  (numerical)
	Installment rate in percentage of disposable income

Attribute 9:  (qualitative)
	Personal status and sex
	A91 : male   : divorced/separated
	A92 : female : divorced/separated/married
    A93 : male   : single
	A94 : male   : married/widowed
	A95 : female : single

Attribute 10: (qualitative)
	Other debtors / guarantors
	A101 : none
	A102 : co-applicant
	A103 : guarantor

Attribute 11: (numerical)
	Present residence since

Attribute 12: (qualitative)
	Property
	A121 : real estate
	A122 : if not A121 : building society savings agreement/ life insurance
    A123 : if not A121/A122 : car or other, not in attribute 6
	A124 : unknown / no property

Attribute 13: (numerical)
	Age in years

Attribute 14: (qualitative)
	Other installment plans 
	A141 : bank
	A142 : stores
	A143 : none

Attribute 15: (qualitative)
	Housing
	A151 : rent
	A152 : own
	A153 : for free

Attribute 16: (numerical)
    Number of existing credits at this bank

Attribute 17: (qualitative)
	Job
	A171 : unemployed/ unskilled  - non-resident
	A172 : unskilled - resident
	A173 : skilled employee / official
	A174 : management/ self-employed/ highly qualified employee/ officer

Attribute 18: (numerical)
	Number of people being liable to provide maintenance for

Attribute 19: (qualitative)
	Telephone
	A191 : none
	A192 : yes, registered under the customers name

Attribute 20: (qualitative)
	foreign worker
	A201 : yes
	A202 : no
```