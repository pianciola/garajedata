# Modelos 3D

Poné acá los modelos de los autos en formato **.glb**. La app los carga solos, los
escala a tamaño real y pinta la carrocería con el color elegido.

## Forma simple: un archivo por carrocería

Nombrá cada archivo con el tipo de carrocería:

`hatchback.glb` · `sedan.glb` · `rural.glb` · `coupe.glb` · `suv.glb` · `pickup.glb` · `utilitario.glb`

## Con `modelos.json` (archivos con otro nombre, o varios autos en uno)

```json
{
  "sedan": {
    "archivo": "pack.glb",
    "nodo": "Sedan",
    "pintura": ["Body_Paint"],
    "rotacion": 0,
    "credito": "\"Generic passenger car pack\" de Comrade1280 (CC BY 4.0)",
    "url": "https://sketchfab.com/3d-models/20f9af9b8a404d5cb022ac6fe87f21f5"
  }
}
```

Todos los campos son opcionales:

- `archivo`: el nombre del `.glb`.
- `nodo`: el objeto dentro del archivo, cuando el `.glb` trae varios autos.
- `pintura`: los materiales que se pintan. Si no lo ponés, se detectan solos.
- `rotacion`: grados de giro extra, por si el modelo viene mal orientado.
- `largo`: el largo en metros al que se escala el modelo.
- `credito` y `url`: el autor y su enlace. Se muestran en el pie de la página.

## Licencias

Si un modelo es **CC BY**, la licencia obliga a citar al autor: completá `credito` y `url`.
No uses modelos con licencias **NonCommercial** o **NoDerivatives** si vas a publicar la página.

Conviene usar archivos de menos de 10 MB para que la página cargue rápido.
