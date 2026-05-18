# Ética y Derecho Informático — Test

Web para practicar el examen tipo test de **Ética y Derecho Informático**.

## Funciones

- **Simulacro de examen**: 60 preguntas aleatorias (como en el examen real)
- **Preguntas aleatorias**: elige cuántas quieres practicar
- **Por tema**: 8 bloques temáticos del temario
- **Ver respuesta**: muestra la opción correcta y una breve explicación
- **Preguntas falladas**: guarda automáticamente los fallos (en este navegador) y permite repasarlos hasta acertarlas

## Uso local

```bash
cd etica
python3 -m http.server 8080
```

Abre [http://localhost:8080](http://localhost:8080)

## Regenerar preguntas desde los PDF

Si actualizas los PDFs del banco de preguntas:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pypdf
python3 scripts/extract_pdfs.py   # extrae texto
python3 scripts/build_questions.py # genera data/questions.json
```

## Despliegue (GitHub Pages)

El repositorio está preparado como sitio estático. En GitHub: **Settings → Pages → Source: Deploy from branch → main / root**.
