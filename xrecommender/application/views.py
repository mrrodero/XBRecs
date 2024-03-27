from django.views import generic
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from .forms import SignUpForm

from pyvis.network import Network
# import networkx as nx


class HomeView(generic.TemplateView):
    """Vista basada en clase para la página principal."""

    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        """
        Override del método get_context_data para añadir el contexto

        Author: Álvaro Rodero
        """
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            # Mostrar últimos 5 libros añadidos
            context['user'] = self.request.user
        return context


class SignupView(generic.CreateView):
    """Vista basada en clase para el registro de usuarios."""

    form_class = SignUpForm
    template_name = 'registration/signup.html'

    def get(self, request, *args, **kwargs):
        """
        Override del método get para mostrar el formulario de registro

        ## Argumentos:
        - `request`: Petición HTTP.
        """
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        """
        Override del método post para registrar al usuario

        ## Argumentos:
        - `request`: Petición HTTP.
        """
        form = self.form_class(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=raw_password)
            login(request, user)
            return redirect('home')
        return render(request, self.template_name, {'form': form})


class RecommendView(generic.TemplateView):
    """Vista basada en clase para mostrar las recomendaciones."""

    template_name = 'recommender/recommend.html'

    def _generate_random_color(self):
        """
        Genera un color aleatorio.

        ## Retorno:
        - `str`: Color en formato hexadecimal.
        """
        import random
        import seaborn as sns

        color_palette = sns.color_palette('husl', 256)
        color = random.choice(color_palette)
        return f'#{int(color[0]*255):02x}{int(color[1]*255):02x}{int(color[2]*255):02x}'

    def _pyvis_graph_html(self) -> str:
        """
        Método para generar un grafo con la librería Pyvis y
        devolver su código HTML.

        ## Retorno:
        - Código HTML del grafo.
        """
        # Obtener información del usuario para la recomendación
        # self.request.user
        net = Network(height='750px', width='100%', heading='')
        books = [
            '1984', 'Cien años de soledad', 'El señor de los anillos',
            'El principito', 'Don Quijote de la Mancha'
        ]
        covers = [
            'https://images-na.ssl-images-amazon.com/images/S/compressed.photo.goodreads.com/books/1657781256i/61439040.jpg',
            'https://images-na.ssl-images-amazon.com/images/S/compressed.photo.goodreads.com/books/1327881361i/320.jpg',
            'https://images-na.ssl-images-amazon.com/images/S/compressed.photo.goodreads.com/books/1566425108i/33.jpg',
            'https://images-na.ssl-images-amazon.com/images/S/compressed.photo.goodreads.com/books/1367545443i/157993.jpg',
            'https://images-na.ssl-images-amazon.com/images/S/compressed.photo.goodreads.com/books/1546112331i/3836.jpg'
        ]
        for i, (book, cover) in enumerate(zip(books, covers)):
            net.add_node(
                i,
                shape='image',
                label=book,
                title=book,
                image=cover
            )
        keywords = [
            'distopía', 'realismo mágico', 'fantasía', 'infantil', 'clásico'
        ]
        net.add_nodes(
            keywords,
            label=keywords,
            title=keywords
        )
        net.add_edges(
            [
                (0, 'distopía'), (0, 'clásico'),
                (1, 'realismo mágico'), (1, 'clásico'),
                (2, 'fantasía'), (2, 'infantil'), (2, 'clásico'),
                (3, 'infantil'),
                (4, 'clásico'), (4, 'fantasía')
            ]
        )
        # Change size of keyword nodes based on number of edges
        neighbor_map = net.get_adj_list()
        for kw in keywords:
            node = net.get_node(kw)
            node['size'] = 12*len(neighbor_map[kw])
            node['color'] = self._generate_random_color()

        return net.generate_html()

    def get_context_data(self, **kwargs):
        """
        Override del método get_context_data para añadir el contexto

        Author: Álvaro Rodero
        """
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            # Mostrar recomendaciones
            context['net_html'] = self._pyvis_graph_html()
        return context
