from app.pipelines.update_pipeline import UpdatePipeline

#question = "who is the current most richest person in the world"
question = "World FiFA Ranking 2026 bangladesh rank?"
pipeline = UpdatePipeline()
result = pipeline.process_question(question)

print("SEARCH QUERY:", result.get("search_query"))
print("QUESTION:", result["question"])
print("SEARCH RESULTS:", result["search_count"])
print("CRAWLED PAGES:", result["crawled_count"])
print("CONFIDENCE:", result.get("confidence_score"))
print()
print("AI ANSWER:")
print(result.get("ai_answer") or result.get("error") or "No answer")
print()
print("TOP SOURCES:")
for i, s in enumerate((result.get("sources") or [])[:5], 1):
    title = (s.get("title") or "")[:80]
    url = s.get("url") or ""
    print(f"  {i}. {title} | {url}")
