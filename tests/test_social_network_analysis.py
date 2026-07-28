import importlib.util
from pathlib import Path

import networkx as nx


SCRIPT = (
    Path(__file__).parents[1]
    / "skills"
    / "social-network-analysis"
    / "scripts"
    / "generate_sna.py"
)
SPEC = importlib.util.spec_from_file_location("generate_sna", SCRIPT)
SNA = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(SNA)


def sample_rows():
    return [
        {
            "Author": "alice",
            "Content": "Isu air dibahas bersama @brand dan @bob",
            "Engagement": 12,
        },
        {
            "Author": "@bob",
            "Content": "Menanggapi @brand tentang kualitas produk",
            "Engagement": 7,
        },
        {
            "Author": "carol",
            "Content": "Diskusi kualitas dengan @alice dan @brand",
            "Engagement": 3,
        },
        {
            "Author": "alice",
            "Content": "Tanpa mention di post ini",
            "Engagement": 1,
        },
    ]


def test_build_graph_uses_author_to_mention_edges():
    graph, texts, audit = SNA.build_graph(sample_rows())

    assert isinstance(graph, nx.DiGraph)
    assert graph.has_edge("alice", "brand")
    assert graph.has_edge("alice", "bob")
    assert graph.has_edge("bob", "brand")
    assert graph.has_edge("carol", "alice")
    assert audit["posts"] == 4
    assert audit["posts_with_mentions"] == 3
    assert audit["mention_coverage_pct"] == 75.0
    assert texts["alice"]


def test_self_mentions_are_excluded():
    graph, _, audit = SNA.build_graph(
        [{"Author": "@alice", "Content": "@alice mengulang pesan", "Engagement": 1}]
    )

    assert graph.number_of_nodes() == 0
    assert graph.number_of_edges() == 0
    assert audit["isolates_removed"] == 1


def test_visual_subgraph_respects_limits():
    graph, _, _ = SNA.build_graph(sample_rows())
    metrics = SNA.centralities(graph, seed=42)
    visible = SNA.visual_subgraph(graph, metrics, max_nodes=3, max_edges=2)

    assert visible.number_of_nodes() <= 3
    assert visible.number_of_edges() <= 2
