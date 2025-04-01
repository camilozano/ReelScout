# System Patterns: ReelScout

*(This document will outline the high-level architecture, key technical decisions, design patterns, and component relationships as they are established.)*

**Initial Architecture (Conceptual):**

```mermaid
graph TD
    A[User Input (Reel URL)] --> B(Instagram Fetcher);
    B -- Video Data --> C(Video Processor);
    C -- Processed Data --> D(Gemini Analyzer);
    D -- Analysis Results --> E(Output Formatter);
    E --> F[User Output (Insights)];

    subgraph Core Logic
        B
        C
        D
        E
    end

    subgraph External Services
        G[Instagram API/Library]
        H[Google Gemini API]
    end

    B --> G;
    D --> H;
```

**Key Technical Decisions (To Be Made):**

*   **Instagram Library/API:** Which library or method will be used to fetch Reels data? (e.g., `instagrapi`, official API if available, other methods).
*   **Video Processing:** How will video files be handled? Downloaded temporarily? Streamed? What format is needed for Gemini?
*   **Gemini Model:** Which specific Gemini model(s) are best suited for video analysis?
*   **Programming Language/Framework:** What language will the core logic be implemented in? (Likely Python given the AI/ML context).
*   **Data Flow:** How will data be passed between components? Simple function calls? Queues?

**Design Patterns (To Be Identified):**

*   *(Patterns like Facade, Adapter, Strategy might be relevant as the system evolves to handle different APIs or analysis types.)*

**Component Relationships:**

*   The `Instagram Fetcher` is responsible for interacting with Instagram.
*   The `Video Processor` prepares the video data for AI analysis.
*   The `Gemini Analyzer` handles communication with the Gemini API.
*   The `Output Formatter` presents the results.

*(This document will be updated as technical decisions are made and patterns emerge.)*
