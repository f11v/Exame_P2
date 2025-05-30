from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import requests
import logging
import uuid
import time

app = FastAPI()
security = HTTPBearer()

# Configuración de logs estructurados
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
)

class Solicitud(BaseModel):
    tipo: str
    datos: dict

solicitudes_db = {}

# Middleware para logging de cada request
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = time.time()

    logging.info(f"[{request_id}] INICIO {request.method} {request.url.path}")

    try:
        response = await call_next(request)
    except Exception as e:
        logging.error(f"[{request_id}] ERROR: {e}")
        raise

    process_time = round((time.time() - start_time) * 1000, 2)
    logging.info(f"[{request_id}] FIN {request.method} {request.url.path} ({process_time} ms)")
    return response

@app.post("/solicitudes")
async def crear_solicitud(
    solicitud: Solicitud,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    if not verificar_jwt(token):
        logging.warning("Token inválido recibido.")
        raise HTTPException(status_code=401, detail="Token inválido")

    logging.info(f"Solicitud recibida: {solicitud.dict()}")

    response = simular_llamada_soap(solicitud)
    estado = response.get("estado", "en revisión")
    solicitud_id = str(len(solicitudes_db) + 1)
    solicitudes_db[solicitud_id] = {"estado": estado, "datos": solicitud.dict()}
    logging.info(f"Solicitud almacenada con ID {solicitud_id} y estado '{estado}'")

    return {"id": solicitud_id, "estado": estado}

@app.get("/solicitudes/{id}")
async def obtener_solicitud(id: str):
    logging.info(f"Consulta de solicitud con ID {id}")
    return solicitudes_db.get(id, {"detalle": "No encontrada"})

def verificar_jwt(token: str) -> bool:
    return token == "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJteS1rZXkifQ.G4pXwCbCsNJBCBvX7xOw8gbZ3S3VtPzVcBAFzsUZIW0"

# --- Circuit Breaker + Retry + Logging de errores externos ---
fallos_consecutivos = 0
CIRCUIT_BREAKER_UMBRAL = 3
CIRCUIT_BREAKER_TIMEOUT = 60
tiempo_ultimo_fallo = 0

def simular_llamada_soap(solicitud: Solicitud) -> dict:
    global fallos_consecutivos, tiempo_ultimo_fallo

    if fallos_consecutivos >= CIRCUIT_BREAKER_UMBRAL:
        if time.time() - tiempo_ultimo_fallo < CIRCUIT_BREAKER_TIMEOUT:
            logging.warning("CIRCUIT BREAKER ACTIVO. Se omite llamada SOAP.")
            return {"estado": "servicio no disponible (circuit breaker)"}
        fallos_consecutivos = 0  # Reset si pasa el tiempo

    mock_url = "https://8d7f611e-c200-41a8-9373-22c2df4c3af5.mock.pstmn.io/soap"
    headers = {"Content-Type": "text/xml"}
    body = f"""
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                      xmlns:cer="http://certificacion.gob.ec/">
       <soapenv:Header/>
       <soapenv:Body>
          <cer:registrarSolicitud>
             <tipo>{solicitud.tipo}</tipo>
             <nombre>{solicitud.datos.get('nombre')}</nombre>
             <matricula>{solicitud.datos.get('matricula')}</matricula>
          </cer:registrarSolicitud>
       </soapenv:Body>
    </soapenv:Envelope>
    """

    for intento in range(3):
        try:
            logging.info(f"Intento {intento+1} de llamada SOAP")
            response = requests.post(mock_url, headers=headers, data=body, timeout=5)
            if "<estado>procesado</estado>" in response.text:
                fallos_consecutivos = 0
                logging.info("Respuesta SOAP válida recibida.")
                return {"estado": "procesado"}
            return {"estado": "en revisión"}
        except Exception as e:
            fallos_consecutivos += 1
            tiempo_ultimo_fallo = time.time()
            logging.error(f"Fallo SOAP ({intento+1}/3): {str(e)}")
            time.sleep(1)

    return {"estado": "error en conexión con SOAP (reintentos fallidos)"}
