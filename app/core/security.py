import re
from fastapi import Header, HTTPException, status

JWT_REGEX = re.compile(r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$")


def verify_bearer_format(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> str:
    """Verifica que la peticion incluya un Bearer Token con formato sintactico de JWT.

    ============================================================================
    ADVERTENCIA DE CIBERSEGURIDAD / NOTA ACADEMICA:
    Segun la especificacion del profesor para esta practica, esta funcion
    unicamente comprueba la existencia de la cabecera 'Authorization' y que el
    token cumpla con la estructura de tres segmentos Base64URL separados por punto:
        <header>.<payload>.<signature>

    LIMITACION CRITICA:
    Esta comprobacion NO realiza verificacion criptografica de la firma RS256/ES256,
    NO descarga las claves publicas (JWKS) de Keycloak, NO comprueba la vigencia
    temporal (exp / nbf) ni valida emisor (iss) o audiencia (aud).

    EN PRODUCCION ESTO ES VULNERABLE:
    Cualquier atacante podria falsificar un token arbitrario con formato 'aaa.bbb.ccc'
    y seria aceptado por este endpoint. En un entorno real se debe verificar
    criptograficamente la firma contra el endpoint JWKS del Identity Provider (Keycloak).
    ============================================================================
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Encabezado de autorizacion requerido (Authorization: Bearer <token>).",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Formato de autorizacion invalido. Debe usar el esquema Bearer.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]
    if not token or not JWT_REGEX.fullmatch(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token Bearer invalido: debe contener 3 segmentos Base64URL (header.payload.signature).",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
        )

    return token
