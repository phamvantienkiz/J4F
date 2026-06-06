Slide proposal trước khi hackathon bắt đầu, thì nội dung không nên đi quá sâu vào implementation hay code.

Ban tổ chức thường muốn nhìn thấy:

Bạn đã hiểu bài toán chưa?
Giải pháp AI của bạn có hợp lý không?
Kiến trúc có khả thi trong thời gian hackathon không?
Có điểm khác biệt gì so với chatbot thông thường?
Roadmap thực hiện có rõ ràng không?

Tôi đề xuất bộ slide khoảng 10–12 slides như sau.

## Slide 1 - Team Introduction

BurgerPrintsAgent
AI Fulfillment Decision Assistant for POD Sellers

Team: XXX

Hackathon Track: BurgerPrintsAgent (POD Catalog Assistant)

Vision

Help POD sellers find the best fulfillment option within seconds instead of manually comparing thousands of SKUs, factories, shipping methods, and costs.

## Slide 2 - Problem Understanding

Current Challenges for POD Sellers

BurgerPrints ecosystem contains:

Hundreds of products
Multiple fulfillment factories
Thousands of SKUs
Different shipping options
Various taxes and fees
Current Pain Points

Seller must manually:

Search products
Compare factories
Compare shipping times
Calculate margins
Estimate profitability

Result:

Time-consuming
Error-prone
Difficult for new sellers
Slow decision making

### Slide 3 - Our Solution

BurgerPrintsAgent

An AI-powered conversational assistant that helps sellers:

Discover

Find suitable products using natural language.

Compare

Compare fulfillment options across factories.

Evaluate

Calculate costs, shipping, and profit margins.

Execute

(Optional bonus)

Create fulfillment orders directly through BurgerPrints API.

### Slide 4 - User Journey

```
Seller Question
        ↓
AI Understands Intent
        ↓
Retrieve BurgerPrints Data
        ↓
Analyze Constraints
        ↓
Compare Options
        ↓
Recommend Best SKU
        ↓
(Optional)
Create Order
```

Example:

"I want a T-shirt for US market, cost under $8 and shipping under 5 days."

Agent returns:

Best factory
Recommended SKU
Estimated cost
Shipping time
Margin analysis

### Slide 5 - Why AI Agent Instead of Filters?

**Traditional Search**

```
Product Filter
    ↓
Factory Filter
    ↓
Shipping Filter
    ↓
Manual Comparison
```

Seller still does the thinking.

**AI Agent Approach**

```
Seller Goal
    ↓
AI Understands Intent
    ↓
AI Collects Data
    ↓
AI Performs Analysis
    ↓
Decision Recommendation
```

AI becomes a decision-support assistant.

## Slide 6 - Solution Architecture

```
┌─────────────────┐
│ Seller UI       │
│ (Streamlit)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ FastAPI Backend │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ LangGraph Agent │
└────────┬────────┘
         │
 ┌───────┼────────┐
 ▼       ▼        ▼

LLM   Pricing   BurgerPrints
      Engine      API

```

## Slide 7 - AI Agent Workflow

Step 1

Intent Understanding

Extract:

Product type
Market
Budget
Margin target
Shipping requirements
Step 2

Clarification

Ask follow-up questions when information is missing.

Example:

"Do you prioritize lower cost or faster delivery?"

Step 3

Data Retrieval

Use BurgerPrints API to obtain:

Products
Variants
Factories
Pricing
Shipping information
Step 4

Analysis

Calculate:

Total fulfillment cost
Shipping estimates
Profit margins
Cost-performance ranking
Step 5

Recommendation

Generate decision-ready answers.

## Slide 8 - Key AI Capabilities

Natural Language Search

VN / EN support

Examples:

"Áo hoodie nào margin cao nhất?"
"Best T-shirt for US market"
Intelligent Comparison

Compare:

Factory A vs Factory B
Cost
Shipping
Margin
Decision Support

Explain:

Why this SKU
Why this factory
Trade-offs
Multi-turn Conversation

Remember user context during session.

## Slide 9 - Technical Stack

Backend

FastAPI

Reason:

Lightweight
Fast development
Easy deployment
Agent Framework

LangGraph

Reason:

Stateful workflows
Tool calling
Multi-step reasoning
LLM

Google Gemini

Reason:

Function calling
Structured output
Cost-efficient
UI

Streamlit

Reason:

Rapid prototyping
Easy deployment
Great for demos

## Slide 10 - Differentiation

Most Chatbots

Only answer questions.

BurgerPrintsAgent

Can:

✓ Understand seller goals

✓ Analyze fulfillment options

✓ Calculate margins

✓ Recommend best choices

✓ Create orders (bonus)

## Slide 11 - Expected Impact

For New Sellers

Faster onboarding
Reduced learning curve

For Experienced Sellers

Faster product research
Better fulfillment decisions

For BurgerPrints

Higher platform engagement
Increased order conversion
Better seller experience
