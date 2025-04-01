# Product Context: ReelScout

**Problem:** Discovering relevant and high-quality content, particularly specific locations mentioned in travel Reels saved in Instagram Collections, can be time-consuming and inefficient. Manually scrubbing through videos or captions is tedious.

**Solution:** ReelScout aims to provide an intelligent way to extract location data from saved Instagram Reels. By analyzing video captions and/or the video content itself using AI, it can:
*   **Concise Summaries:** Quickly grasp the essence of a Reel without watching the whole thing.
*   **Targeted Recommendations:** Find similar Reels based on content themes, not just superficial tags or engagement metrics.
*   **Deeper Insights:** Understand trends, topics, or sentiments expressed within Reels.

**Target User:** Initially, this could be useful for content creators, marketers, researchers, or anyone looking for a more efficient way to consume or analyze Reels content.

**User Experience Goals:**
*   **Simplicity:** Easy to input a Reel (e.g., by URL) and get results.
*   **Clarity:** Insights generated should be easy to understand and actionable.
*   **Relevance:** The analysis and recommendations should accurately reflect the video's content.

**How it Should Work (Conceptual):**
1.  User provides an Instagram Reel identifier (e.g., URL).
2.  System fetches the Reel video data.
3.  Video data is sent to the Gemini API for analysis.
4.  Gemini processes the video and returns structured insights (summary, keywords, sentiment, etc. - specific outputs TBD).
5.  System presents these insights to the user.

*(This context explains the 'why' behind ReelScout, building upon the 'what' defined in the project brief and the specifics from the README.)*
