"""Chamadas HTTP para os outros microserviços (só biblioteca padrão)."""
import json
import os
import urllib.error
import urllib.request

TIMEOUT = float(os.environ.get("HTTP_TIMEOUT", "3"))


class Indisponivel(Exception):
    """O outro serviço não respondeu (rede, timeout ou erro 5xx)."""


def chamar(metodo, url, corpo=None):
    """Devolve (status, json). 4xx volta normalmente; falha de rede ou 5xx vira Indisponivel."""
    dados = json.dumps(corpo).encode() if corpo is not None else None
    req = urllib.request.Request(url, data=dados, method=metodo, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, json.loads(resp.read() or b"null")
    except urllib.error.HTTPError as err:
        if err.code >= 500:
            raise Indisponivel(url) from err
        try:
            return err.code, json.loads(err.read() or b"null")
        except ValueError:
            return err.code, None
    except (urllib.error.URLError, TimeoutError, ValueError) as err:
        raise Indisponivel(url) from err


def url(nome, caminho):
    return os.environ[f"{nome.upper()}_URL"].rstrip("/") + caminho
