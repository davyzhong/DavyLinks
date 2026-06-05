"""Tests for immutability guarantees in scan_articles and summarize."""

import copy


def test_filter_by_keywords_does_not_mutate_input():
    from scan_articles import filter_by_keywords

    articles = [
        {"title": "AI 大模型发布", "url": "https://a.example", "source": "36氪", "description": "AI news"},
        {"title": "Cooking recipe", "url": "https://b.example", "source": "Food Blog", "description": "Food"},
    ]
    original = copy.deepcopy(articles)
    config = {
        "global_keywords": ["AI", "大模型"],
        "sources": [{"name": "36氪", "category": "科技创投", "weight": 5, "keywords": []}],
    }

    filter_by_keywords(articles, config)

    assert articles == original, "filter_by_keywords mutated input articles"


def test_filter_by_keywords_adds_score_to_output_not_input():
    from scan_articles import filter_by_keywords

    articles = [
        {"title": "AI 大模型 GPT 发布", "url": "https://a.example", "source": "36氪"},
    ]
    config = {
        "global_keywords": ["AI", "大模型", "GPT"],
        "sources": [{"name": "36氪", "category": "科技创投", "weight": 5, "keywords": []}],
    }

    result = filter_by_keywords(articles, config)

    assert "relevance_score" not in articles[0], "Input article was mutated with relevance_score"
    assert len(result) == 1
    assert result[0]["relevance_score"] >= 8
    assert result[0]["category"] == "科技创投"


def test_hash_url_returns_64bit():
    from scan_articles import hash_url

    h = hash_url("https://example.com/test")
    # 16 hex chars = 64 bits, max value = 2^64 - 1
    assert h < 2**64
    assert h > 2**32  # Statistically should be larger than 32-bit range


def test_hash_url_deterministic():
    from scan_articles import hash_url

    assert hash_url("https://example.com") == hash_url("https://example.com")
    assert hash_url("https://a.com") != hash_url("https://b.com")


def test_final_sort_does_not_mutate_input():
    from summarize import final_sort

    articles = [
        {"title": "A", "relevance_score": 10, "quality_rating": 3, "cross_source_score": 0},
        {"title": "B", "relevance_score": 5, "quality_rating": 5, "cross_source_score": 15},
    ]
    original = copy.deepcopy(articles)

    result = final_sort(articles)

    assert articles == original, "final_sort mutated input articles"
    # B should be first: 5 + 10 + 15 = 30 vs A: 10 + 6 + 0 = 16
    assert result[0]["title"] == "B"
    assert "final_score" not in articles[0], "Input article was mutated with final_score"


def test_summarize_one_does_not_mutate_input():
    from summarize import summarize_one

    article = {"title": "Test", "source": "Src", "description": "Desc"}
    original = dict(article)
    llm_config = {"name": "test", "api_key": "k", "base_url": "http://x", "model": "m", "format": "openai"}

    # Mock call_llm to avoid network
    import summarize as s
    original_call = s.call_llm
    s.call_llm = lambda cfg, prompt: "summary text"
    try:
        result = summarize_one(article, llm_config)
    finally:
        s.call_llm = original_call

    assert article == original, "summarize_one mutated input article"
    assert result["summary"] == "summary text"
    assert result["summarized_by"] == "test"


def test_summarize_parallel_preserves_position_on_failure():
    """When a future returns None, position must stay aligned — not collapse the list."""
    from summarize import summarize_parallel

    articles = [
        {"title": f"Art {i}", "source": "Src", "description": "D"} for i in range(3)
    ]
    originals = copy.deepcopy(articles)

    # Mock: art[1] always fails all LLMs, art[0] and art[2] succeed
    import summarize as s
    original_one = s.summarize_one

    def mock_summarize_one(article, llm_config):
        if article["title"] == "Art 1":
            raise RuntimeError("simulated LLM failure")
        return {**article, "summary": f"ok-{article['title']}", "tags": [], "quality_rating": 3, "summarized_by": llm_config["name"]}

    s.summarize_one = mock_summarize_one
    try:
        results = summarize_parallel(articles, [{"name": "test", "api_key": "k", "base_url": "http://x", "model": "m", "format": "openai"}])
    finally:
        s.summarize_one = original_one

    # Position preserved: results[0] = Art 0, results[1] = Art 1 (failed), results[2] = Art 2
    assert len(results) == 3
    assert results[0]["title"] == "Art 0"
    assert results[0]["summary"] == "ok-Art 0"
    assert results[1]["title"] == "Art 1"
    assert results[1]["summary"] == "(所有LLM摘要均失败)"
    assert results[2]["title"] == "Art 2"
    assert results[2]["summary"] == "ok-Art 2"

    # Input not mutated
    assert articles == originals
