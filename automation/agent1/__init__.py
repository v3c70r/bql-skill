"""Agent 1 Corpus Builder automation script."""
from agent1.corpus_builder import CorpusBuilder

if __name__ == "__main__":
    builder = CorpusBuilder()
    builder.run_full_corpus_build()
