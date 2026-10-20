from fastapi.testclient import TestClient
import pytest
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def lifespan():
    global client
    with TestClient(app) as active_client:
        client = active_client
        yield

# Cadena sintética: comprueba solo formato; no es un JWT emitido por un IdP.
DUMMY_VALID_JWT = "testHeader.testPayload.testSignature"


def test_health_check_is_public():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_get_games_unauthorized_without_header():
    response = client.get("/api/games")
    assert response.status_code == 401
    assert "WWW-Authenticate" in response.headers


def test_get_games_unauthorized_with_bad_scheme():
    response = client.get("/api/games", headers={"Authorization": "Basic dXNlcjpwYXNz"})
    assert response.status_code == 401
    assert "Bearer" in response.headers.get("WWW-Authenticate", "")


def test_get_games_unauthorized_with_malformed_token():
    response = client.get("/api/games", headers={"Authorization": "Bearer not-a-jwt-format"})
    assert response.status_code == 401


def test_get_games_authorized_with_dummy_bearer_format():
    response = client.get(
        "/api/games",
        headers={"Authorization": f"Bearer {DUMMY_VALID_JWT}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_post_game_authorized():
    new_game = {
        "title": "Hollow Knight: Silksong",
        "genre": "Metroidvania",
        "platform": "PC / Consolas",
        "release_year": 2025,
    }
    response = client.post(
        "/api/games",
        json=new_game,
        headers={"Authorization": f"Bearer {DUMMY_VALID_JWT}"},
    )
    assert response.status_code == 201
    created = response.json()
    assert created["id"] is not None
    assert created["title"] == new_game["title"]
    assert created["genre"] == new_game["genre"]


@pytest.mark.parametrize("method", ["get", "post"])
@pytest.mark.parametrize("header", [None, "Basic abc", "Bearer", "Bearer abc", "Bearer a.b.", "Bearer a.b.c d", "Bearer  a.b.c"])
def test_protection_for_both_methods(method, header):
    headers = {"Authorization": header} if header else {}
    response = getattr(client, method)("/api/games", headers=headers)
    assert response.status_code == 401


def test_forged_token_deliberately_accepted():
    assert client.get("/api/games", headers={"Authorization": "bEaReR aaa.bbb.ccc"}).status_code == 200


@pytest.mark.parametrize("origin,allowed", [("http://localhost:4200", True), ("https://example.org", False)])
def test_cors_preflight(origin, allowed):
    response = client.options("/api/games", headers={"Origin": origin, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "authorization,content-type"})
    assert response.status_code == (200 if allowed else 400)
    assert (response.headers.get("access-control-allow-origin") == origin) is allowed


@pytest.mark.parametrize("title,year", [("   ",2026),("Valid",1800),("Valid",2101)])
def test_invalid_game(title, year):
    response = client.post("/api/games", headers={"Authorization":"Bearer a.b.c"}, json={"title":title,"genre":"RPG","platform":"PC","release_year":year})
    assert response.status_code == 422
