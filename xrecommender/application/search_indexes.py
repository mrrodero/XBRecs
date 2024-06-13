from haystack import indexes
from .models import Book


class BookIndex(indexes.SearchIndex, indexes.Indexable):
    """Índice de libros para la búsqueda."""
    text = indexes.CharField(
        document=True, use_template=True
    )
    title = indexes.CharField(model_attr='title')
    isbn = indexes.CharField(model_attr='isbn')

    def get_model(self):
        """Devuelve el modelo que será indexado."""
        return Book
