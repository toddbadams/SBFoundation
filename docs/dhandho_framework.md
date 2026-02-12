### Problem:

You’ve heard the term “Dhandho Framework” tossed around in investing circles and want to know what it *actually* means—and how it can be useful.

### Solution:

The **Dhandho Framework** is an investment philosophy popularized by **Mohnish Pabrai**, a value investor who modeled much of his strategy after Warren Buffett. “Dhandho” is a Gujarati word that loosely translates to “endeavors that create wealth.” At its core, this framework is about making *low-risk, high-uncertainty bets*—essentially maximizing upside while minimizing downside.

---

## 🧠 The Core Principles of the Dhandho Framework

Here’s the breakdown:

### 1. **Invest in Existing Businesses**

No need to reinvent the wheel. Dhandho focuses on proven, cash-generating businesses with understandable models. Think gas stations, insurance, or consumer brands.

### 2. **Invest in Simple Businesses**

If you can't explain the business to a 10-year-old in five minutes, it's too complex. Dhandho is all about clarity.

### 3. **Invest in Distressed Businesses in Distressed Industries**

When there's blood in the streets, value investors go shopping. The framework thrives on pessimism in the market that leads to bargain buys.

### 4. **Invest in Businesses with Durable Moats**

Look for companies with sustainable competitive advantages—brand, scale, network effects, switching costs, etc.

### 5. **Bet Heavily When the Odds Are in Your Favor**

This is the “Heads I win, tails I don’t lose much” mentality. Dhandho encourages concentrated bets when the margin of safety is high.

### 6. **Focus on Arbitrage**

Pabrai uses this loosely—it includes classic arbitrage but also means exploiting pricing inefficiencies (like buying a dollar for 50 cents).

### 7. **Margin of Safety**

Borrowed from Ben Graham and Buffett. Always leave a buffer between your buy price and intrinsic value to protect your downside.

### 8. **Low Risk, High Uncertainty**

This is *key*. Dhandho seeks investments that are **not risky** (in terms of potential permanent capital loss), but may appear risky due to **uncertainty**. Markets often confuse the two—and therein lies the opportunity.

---

## 📊 Example in Action

Let’s say a family-run motel chain is struggling due to a temporary regional downturn. It’s profitable, debt-free, and has hard assets like real estate. The stock is trading at half of book value.

To a Dhandho investor, that’s not risky—it’s a *misunderstood* opportunity.

---

## 🧭 In Summary

The Dhandho Framework is:

* Rational
* Conservative
* Opportunistic

It's the investing version of “Don’t do anything unless the odds are wildly in your favor—and then swing hard.”

Let me know if you want a cheat sheet or want to see how it might map to algo-driven strategies.


### Problem:

You're trying to figure out **how much** to bet or invest when you have a statistical edge—but you don’t want to overextend and blow up your account.

### Solution:

Enter the **Kelly Formula**—a position sizing formula that maximizes long-term growth of capital **while minimizing risk of ruin**. It was originally developed for optimal bet sizing in gambling, but it’s just as relevant in investing, trading, and portfolio management.

---

## 🎯 What Is the Kelly Formula?

At its core, the **Kelly Criterion** tells you **what percentage of your capital to allocate** to a given opportunity based on the expected edge and the odds of success.

### The Basic Formula (for binary outcomes):

$$
f^* = \frac{bp - q}{b}
$$

Where:

* $f^*$ = fraction of capital to bet/invest
* $b$ = odds received on the bet (i.e. net odds; 2:1 payout → $b = 2$)
* $p$ = probability of winning
* $q = 1 - p$ = probability of losing

---

## 📈 Example: Investing Context

Say you have a strategy that wins **60% of the time** ($p = 0.6$), and when it wins, it returns **2x** your stake (so $b = 2$):

$$
f^* = \frac{(2)(0.6) - 0.4}{2} = \frac{1.2 - 0.4}{2} = \frac{0.8}{2} = 0.4
$$

You should invest **40% of your capital** each time using that strategy.

---

## 🧠 For Trading/Investing (continuous returns)

In investing, outcomes aren't binary, so a modified version of Kelly is used:

$$
f^* = \frac{\mu - r_f}{\sigma^2}
$$

Where:

* $\mu$ = expected return
* $r_f$ = risk-free rate
* $\sigma^2$ = variance of returns

This version tells you **what proportion of your capital to allocate to a single asset** in a portfolio.

---

## ⚠️ Key Tradeoffs

### ✅ Pros:

* Maximizes long-term growth rate
* Mathematically optimal under known probabilities
* Avoids ruin

### ❌ Cons:

* Assumes you know your edge with precision (you probably don’t)
* Can be very aggressive (100%+ allocations)
* **Volatility is high**—you win big *and* lose big

### 🧘 Practical Tip: Use **Half-Kelly**

Most professionals use **½ Kelly** or even **¼ Kelly** to reduce drawdowns and smooth out volatility, especially when your edge is uncertain.

---

## 🧭 In Summary

The Kelly Formula is a weaponized position sizing tool:

* Use it when you have an edge
* Use **caution** if your edge isn't rock solid
* Consider fractional Kelly for sanity

Want help plugging your trading stats into it? I can run the numbers.
