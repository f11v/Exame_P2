
# SolicitudService

Este microservicio REST permite la creación y consulta de solicitudes académicas, integrando un servicio SOAP simulado.

## Endpoints

- `POST /solicitudes` - Crea una solicitud
- `GET /solicitudes/{id}` - Obtiene una solicitud por ID

## Requisitos

- FastAPI
- Uvicorn

## Ejecución

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Autenticación

Se requiere un token JWT simulado en la cabecera Authorization:

```
Authorization: Bearer valid-token
```
