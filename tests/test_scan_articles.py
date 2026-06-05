import sys


def test_cluster_by_topic_compares_chinese_similarity_across_entity_buckets():
    sys.path.insert(0, "scripts")
    from scan_articles import cluster_by_topic

    articles = [
        {
            "title": "DeepSeek 发布新模型，性能大幅提升",
            "url": "https://a.example",
            "source": "A",
            "relevance_score": 10,
        },
        {
            "title": "DeepSeek 新模型上线，能力提升明显",
            "url": "https://b.example",
            "source": "B",
            "relevance_score": 9,
        },
        {
            "title": "发布新模型性能大幅提升",
            "url": "https://c.example",
            "source": "C",
            "relevance_score": 8,
        },
        {
            "title": "新模型性能大幅提升发布",
            "url": "https://d.example",
            "source": "D",
            "relevance_score": 8,
        },
    ]

    clusters = cluster_by_topic(articles)

    assert len(clusters) == 1
    assert clusters[0]["cluster_size"] == 4
    assert clusters[0]["source_count"] == 4
