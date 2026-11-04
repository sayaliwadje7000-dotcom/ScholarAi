from dataclasses import dataclass


@dataclass(frozen=True)
class ChunkingSettings:
    """Configuration for document text chunking."""

    chunk_size: int = 1000
    chunk_overlap: int = 150
    minimum_chunk_size: int = 100
    preserve_page_boundaries: bool = True

    def __post_init__(self):
        if not isinstance(self.chunk_size, int) or isinstance(self.chunk_size, bool):
            raise ValueError("Chunk size must be an integer.")

        if not isinstance(self.chunk_overlap, int) or isinstance(self.chunk_overlap, bool):
            raise ValueError("Chunk overlap must be an integer.")

        if not isinstance(self.minimum_chunk_size, int) or isinstance(self.minimum_chunk_size, bool):
            raise ValueError("Minimum chunk size must be an integer.")

        if self.chunk_size <= 0:
            raise ValueError("Chunk size must be greater than zero.")

        if self.chunk_overlap < 0:
            raise ValueError("Chunk overlap cannot be negative.")

        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("Chunk overlap must be smaller than chunk size.")

        if self.minimum_chunk_size <= 0:
            raise ValueError("Minimum chunk size must be greater than zero.")

        if self.minimum_chunk_size > self.chunk_size:
            raise ValueError("Minimum chunk size cannot exceed chunk size.")

        if not isinstance(self.preserve_page_boundaries, bool):
            raise ValueError("preserve_page_boundaries must be boolean.")