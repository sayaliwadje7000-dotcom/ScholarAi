from app.services.educational_resources.discovery_evaluation import (
    DiscoveryEvaluator,
)


ranked_resources = [
    "youtube_ml_course",
    "openalex_ml_paper",
    "random_blog",
    "crossref_ml_article",
    "google_books_ml_book",
]


relevance_judgments = {
    "youtube_ml_course": 3,
    "openalex_ml_paper": 3,
    "random_blog": 0,
    "crossref_ml_article": 2,
    "google_books_ml_book": 2,
}


metrics = DiscoveryEvaluator.evaluate(
    ranked_resource_ids=ranked_resources,
    relevance=relevance_judgments,
    k=5,
)


print("\nRESOURCE DISCOVERY EVALUATION")
print("-" * 40)

for metric, value in metrics.to_dict().items():
    print(f"{metric}: {value}")

print("-" * 40)