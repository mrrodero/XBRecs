# Guía de instalación y uso del sistema recomendador XBRecs

## Servidor web local

Para probar el sistema en local, deberás solicitar acceso a la base de datos contactando con
[mrrodero](mailto:alvaro.rodero.s@gmail.com)

Una vez tengas acceso, debes seguir estos pasos:

1. Accede a la carpeta **xrecommender**.
2. Ejecuta, desde la terminal en que vayas a lanzar el servidor, `EXPORT DEBUG=True`.
3. Ahora, lanza el sistema con el comando `make runserver`.
4. ¡Listo! Ya puedes empezar a utilizar el sistema, creando un perfil de usuario y añadiendo libros que hayas leído. Podrás acceder a la recomendación desde la vista principal de la web.

## Servidor web online

Aunque se recomienda probar la web localmente, también puedes probar el sistema recomendador XBRecs accediendo a su versión [desplegada](https://xbrecs-render.onrender.com) en Render. Sin embargo, es posible que a la hora de generar una recomendación, el servidor tarde demasiado o deje de funcionar. Esto se debe a la latencia con la base de datos remota de NeonTech.
