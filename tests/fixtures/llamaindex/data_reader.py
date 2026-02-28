"""LlamaIndex data reader / connector usage — test fixture."""

from llama_index.readers.web import SimpleWebPageReader

reader = SimpleWebPageReader(html_to_text=True)
documents = reader.load_data(urls=["https://example.com/data"])
