# **Project Clare: AI Tutor Enhancement (MVP Plan)**

## **1\. Introduction & Current Situation**

We have received a detailed proposal for a significant upgrade to our AI Tutor chatbot, centered on "Clare's Intelligent Memory & Interaction Reinforcement System". The plan is outlined across three key documents:

* **4\. Clare’s “Intelligent Memory & Interaction Reinforcement System” 方案.docx (and its English translation)**: This is the core strategy document. It details the system's unique market position, which focuses on integrating a forgetting curve-based reinforcement schedule and continuous personalization—features lacking in competing products. It outlines a sophisticated system with features like a dual-card UI, a retention bar, dynamic mastery badges, and embedded Responsible AI prompts.  
* **3\. Weekly Reinforcement Table for Clare.docx**: This document provides the content foundation for the system. It contains 11 weeks of course material (Weeks 0-10) for a Generative AI course, broken down into topics, core questions, and key knowledge points. It also defines a detailed weighting system for spaced repetition at T+7, T+14, and T+30 intervals.

Our Current Situation:  
The full proposal is comprehensive but complex. Our immediate goal is to define a Minimum Viable Product (MVP). We need to distill the proposal down to its core, demonstrable features. The MVP must showcase the project's key innovations—specifically the visible application of the forgetting curve—without building the entire adaptive system upfront. Features that are difficult to implement or not immediately visible in a demo will be deferred.

## **2\. MVP Mapping**

This roadmap focuses on delivering a functional demo that proves the core concepts of the proposal.

### **Phase 1: Content Foundation & Core Logic (Backend)**

The goal is to load the necessary content and implement the simplest version of the reinforcement logic.

* **Task 1: Ingest Course Content**  
  * Structure and import the content from the Weekly Reinforcement Table. Each content piece (Key Knowledge Point, Core Question) must be tagged with its corresponding week (0-10).  
* **Task 2: Implement Simplified Spaced Repetition Logic**  
  * Develop a content sampling function based **only on the T+7 (weekly) review schedule**.  
  * This function will use the fixed weights defined in the content document: Current week: 8%, W-1: 12%, W-2: 20%, W-3: 25%, W-4: 35%. The more complex T+14 and T+30 schedules will be ignored for the MVP.

### **Phase 2: Core UI & Presentation (Frontend)**

The goal is to build the innovative, visible components that demonstrate the "why" behind the content selection.

* **Task 1: Build the Dual-Card UI**  
  * Develop a fixed two-card component in the chat interface.  
  * **Left Card ("Core Knowledge")**: This card will be populated by the content selected from the T+7 sampling function created in Phase 1\.  
  * **Right Card ("Common Questions")**: For the MVP, this will be simplified. Instead of analyzing personal logs, it will display the 3 "Core Questions" from the *current* week's material.  
* **Task 2: Build the Intelligent Retention Bar**  
  * Create the timeline visualization below the dialogue box.  
  * This bar will visually highlight the weights for the current T+7 review window, making it clear to the user why they are seeing content from previous weeks.  
* **Task 3: Add Responsible Micro-Prompts**  
  * Append a static, reflective question to each item displayed in the cards. Examples include "Can you give an example?" or "How does this relate to bias/fairness?". This demonstrates the feature without requiring complex logic.

### **Phase 3: Basic Interactivity & Feedback Loop**

The goal is to create a simple feedback mechanism to show how user interaction can influence the system.

* **Task 1: Implement Mastery Badges & "Check Yourself" Button**  
  * Add a status label (e.g., "Unmastered", "Mastered") to each content item. All items will start as "Unmastered".  
  * Include a "Check Yourself" button with each item. For the MVP, this can link to a simple question or a self-assessment confirmation.  
* **Task 2: Implement Simplified De-Prioritization Logic**  
  * When an item is answered correctly via the "Check Yourself" quiz or manually marked as "Mastered", its status changes.  
  * **Simplified Logic**: The system will simply **exclude** any item marked "Mastered" from future T+7 content sampling. This avoids the need for a complex re-weighting algorithm in the MVP.

## **3\. Post-MVP / Deferred Features**

The following features from the original proposal are explicitly out of scope for the MVP but are targeted for future development:

* **Dynamic Learner Profiling**: The initialization questionnaire and the Learner Output Template will not be implemented. The MVP will assume a single, standard learner profile.  
* **Adaptive Content Ratios**: The logic to shift the content ratio (e.g., from 60:40 to 80:20) based on cognitive load will be deferred.  
* **Advanced Spaced Repetition Schedules**: The T+14 and T+30 review cycles will not be part of the MVP.  
* **Multimodal Flashcards**: The system will not adapt content presentation (text vs. visuals) based on learning style for the MVP.  
* **Comprehensive Evaluation Metrics**: Full backend tracking of detailed system metrics is not an MVP requirement.

## **4\. Brainstorming: Interaction Models for MVP**

To ensure the new feature is integrated effectively, we explored several interaction models. The goal is to find a model that is feasible for an MVP, fits within the project's scope, and provides a good user experience.

### **Scheme 1: The Smart Review Dashboard (Decoupled UI)**

*   **User Experience:** A dedicated, persistent UI section (e.g., a sidebar or a panel above the chat) displays review content based on the forgetting curve algorithm. The user can interact with this dashboard (e.g., mark items as "mastered") independently, without interrupting their ongoing chat conversation with the AI tutor. The chat and review functions operate in parallel as two separate features.
*   **MVP Feasibility:** **Very High**. This approach requires no changes to the existing complex agentic workflow, isolating the new feature and minimizing risk. Implementation would be contained within the Streamlit frontend (`main.py`) and a new, separate backend workflow (`repetition_workflow.py`).

### **Scheme 3: On-Demand Review Mode (Triggered Conversation)**

*   **User Experience:** The user initiates a review session by clicking a button (`[Start Review]`) or typing a command (`/review`) in the chat. The AI tutor then switches its mode from a general Q&A agent to a dedicated review agent, guiding the user through questions within the chat interface. The user can exit the review mode with another command.
*   **MVP Feasibility:** **Medium**. This requires modifying the core `agentic_workflow.py` to handle state management (switching between "qa" and "review" modes). While feasible, it introduces more complexity and risk compared to Scheme 1.

### **Scheme 4: The Interactive Dashboard (Hybrid Model)**

*   **User Experience:** This model combines the visual clarity of Scheme 1 with the conversational nature of Scheme 3. The user sees the Smart Review Dashboard with content cards. Clicking on a specific card (e.g., "What is Embedding?") does not simply reveal an answer; it triggers a focused, mini-conversation or quiz about that topic within the main chat window.
*   **MVP Feasibility:** **Medium-High**. It builds upon Scheme 1 but adds the conversational trigger logic of Scheme 3. This is more complex than Scheme 1 but more structured and less risky than a full mode-switching system.

## **5\. Recommendation for Development Path**

After analyzing the alternatives, the following strategic path is recommended:

1.  **MVP Implementation: Adopt Scheme 1 (The Smart Review Dashboard).**
    *   **Reasoning:** This approach perfectly aligns with MVP principles. It allows us to validate the core hypothesis—that a proactive, forgetting-curve-based review feature is valuable to students—with the lowest possible implementation cost and risk. By keeping the new feature's logic completely separate from the existing chatbot workflow, we ensure stability and rapid development.

2.  **Post-MVP Evolution: Evolve towards Scheme 4 (The Interactive Dashboard).**
    *   **Reasoning:** Once the core value of the review feature is validated with the MVP, Scheme 4 provides an elegant and powerful path for enhancement. It seamlessly connects the proactive content recommendations with the core conversational experience of the AI tutor, creating a more integrated and intelligent learning tool without the full complexity of a free-form review mode.