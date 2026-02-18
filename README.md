# Multi-agent-systems-with-ADK

This repository implements a multi-agent **“Moot Court”** system designed to debate and evaluate historical figures. Built as a learning project for the **Build Multi-Agent Systems with ADK** course on **Google Cloud Skills Boost**, it demonstrates **sequential**, **parallel**, and **looping** agent workflows using **Google ADK**.

---

# Moot Court Agent Structure and Workflow

This document explains the architecture and operation of a multi-agent system designed to simulate the investigation and judgment of historical figures (a “Moot Court”).

## Agent Architecture

The diagram below illustrates the relationships and data flow between the agents in the system.

```mermaid
graph TD
    subgraph "Moot Court Process"
        direction LR
        A[root_agent] -- "1. Receive historical figure name from user" --> B(The_Inquiry);

        subgraph The_Inquiry [SequentialAgent]
            direction TB
            B -- "2. Start the process" --> C{The_Trial_And_Review};
            C -- "4. After deliberation is complete" --> D[Verdict];
        end

        subgraph The_Trial_And_Review [LoopAgent - up to 3 iterations]
            direction TB
            C -- "3. Begin investigation and deliberation" --> E(The_Investigation);
            E -- "Provide findings" --> F[judge];
            F -- "Give feedback (if needed)" --> E;
        end

        subgraph The_Investigation [ParallelAgent]
            direction TB
            E -- "Research" --> G[The_Critic];
            E -- "Research" --> H[The_Admirer];
        end

        D -- "5. Save final report" --> I([Output: .txt]);
    end
