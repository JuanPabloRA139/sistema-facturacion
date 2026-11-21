import json
import io
import os
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import date,timedelta
from http.client import HTTPConnection
from pathlib import Path
from servidor import Servidor, Peticion

class CanalEnMemoria:
    def __init__(self,peticion):
        self.entrada=io.BytesIO(peticion)
        self.salida=io.BytesIO()
    def settimeout(self,_): pass
    def makefile(self,*_): return self.entrada
    def sendall(self,datos): self.salida.write(datos)

class FlujoHTTP(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.s=Servidor(Path(self.temp.name)/"prueba.db")
        self.hilo=threading.Thread(target=self.s.serve_forever,daemon=True)
        self.hilo.start()
        self.tokens={}
        for u in ("admin","operador","operador2","auditor"):
            status,_,cookie=self.peticion("entrar",{"usuario":u,"clave":self.s.clave(u)})
            self.assertEqual(status,200)
            self.tokens[u]=cookie.split(";")[0]
    def tearDown(self):
        self.s.shutdown();self.hilo.join();self.s.server_close();self.temp.cleanup()
    def peticion(self,accion,p,usuario=None):
        if not os.environ.get("PRUEBA_CON_RED"):
            cuerpo=json.dumps(p).encode()
            cabecera=(f"POST /api/{accion} HTTP/1.0\r\nHost: 127.0.0.1:{self.s.server_port}\r\n"
                      f"Origin: {self.s.origen}\r\nContent-Type: application/json\r\n"
                      f"Cookie: {self.tokens.get(usuario,'')}\r\nContent-Length: {len(cuerpo)}\r\n\r\n")
            canal=CanalEnMemoria(cabecera.encode()+cuerpo)
            Peticion(canal,("127.0.0.1",0),self.s)
            cab,contenido=canal.salida.getvalue().split(b"\r\n\r\n",1)
            cookie=next((l[12:] for l in cab.decode().splitlines() if l.startswith("Set-Cookie: ")),None)
            return int(cab.split()[1]),json.loads(contenido),cookie
        c=HTTPConnection("127.0.0.1",self.s.server_port,timeout=8)
        c.request("POST","/api/"+accion,json.dumps(p),{"Origin":self.s.origen,"Content-Type":"application/json","Cookie":self.tokens.get(usuario,"")})
        r=c.getresponse(); data=json.loads(r.read()); cookie=r.getheader("Set-Cookie");c.close()
        return r.status,data,cookie
    def test_recorrido(self):
        def ok(a,p,u="operador"):
            status,r,_=self.peticion(a,p,u);self.assertEqual(status,200,r);return r
        self.assertEqual(self.peticion("inicio",{})[0],401)
        inicio=ok("inicio",{}); self.assertEqual((len(inicio["servicios"]),len(inicio["caracteristicas"])),(100,50))
        cid=ok("cliente",{"nombre":"O'Connor","rfc":"ZETA000229AB1"})["cliente"]
        self.assertEqual(self.peticion("cliente",{"nombre":"X","rfc":"ZETA010229AB1"},"operador")[0],400)
        p={"cliente":cid,"clave":"prueba","conceptos":[{"servicio":1,"cantidad":10},{"servicio":2,"cantidad":1}]}
        with ThreadPoolExecutor(2) as pool:
            a,b=list(pool.map(lambda _:ok("emitir",p),range(2)))
        self.assertEqual(a["id"],b["id"]);self.assertEqual(a["total"],123424)
        fid=a["id"]
        self.assertNotEqual(self.peticion("comprobante",{"factura":fid},"operador2")[0],200)
        self.assertEqual(self.peticion("emitir",p,"auditor")[0],403)
        cobro={"factura":fid,"importe":500,"referencia":"p1"}
        for duplicado in (False, True):
            pago = ok("pago",cobro)
            self.assertIs(pago["pago_duplicado"],duplicado)
            self.assertEqual(pago["saldo"],122924)
        self.assertEqual(self.peticion("pago",{**cobro,"importe":501},"operador")[0],400)
        self.assertEqual(self.peticion("pago",{**cobro,"referencia":"p2","importe":999999},"operador")[0],400)
        ok("tarifa",{"servicio":1,"precio":8000},"admin")
        self.assertEqual(ok("comprobante",{"factura":fid})["conceptos"][0]["precio"],10500)
        self.assertEqual(ok("saldos",{})[0]["saldo"],122924)
        f2=ok("emitir",{**p,"clave":"otra"})
        self.assertEqual(ok("cancelar",{"factura":f2["id"],"motivo":"Prueba"},"admin")["estado"],"cancelada")
        ok("asignar",{"servicios":[1,2],"caracteristicas":[8,9]},"admin")
        self.assertTrue(ok("auditoria",{},"auditor"))
        self.assertEqual(ok("cierre",{"periodo":str(date.today()-timedelta(days=1))},"admin")["neto"],0)
        ok("salir",{});self.assertEqual(self.peticion("inicio",{},"operador")[0],401)

    def test_importe_confirmado_y_reintentos(self):
        def hacer(accion, p):
            return self.peticion(accion,p,"operador")[:2]
        nombre = "O'Connor & Hijos <Norte>"
        _,c=hacer("cliente",{"nombre":nombre,"rfc":"ZETA000229AB1"})
        contrato = Path(__file__).resolve().parents[1] / "docs" / "openapi.json"
        emitir = json.loads(contrato.read_bytes())["paths"]["/api/emitir"]["post"]
        ejemplos = emitir["requestBody"]["content"]["application/json"]["examples"]
        p = {**ejemplos["importeConfirmado"]["value"], "cliente": c["cliente"]}
        distinto = {**ejemplos["importeDistinto"]["value"], "cliente": c["cliente"]}
        self.assertEqual(distinto["total_esperado"], p["total_esperado"] - 1)
        codigo, error = hacer("emitir", distinto)
        self.assertEqual(codigo, 409)
        self.assertEqual(error, emitir["responses"]["409"]["content"]["application/json"]["example"])
        self.assertEqual(hacer("inicio",{})[1]["facturas"],[])
        codigo, f = hacer("emitir", p)
        self.assertEqual(codigo, 200)
        self.assertEqual(f["total"], p["total_esperado"])
        self.assertEqual(f["cliente_nombre"],nombre)
        self.assertEqual(hacer("emitir",{**p,"total_esperado":11760})[1]["id"],f["id"])
        self.assertEqual(hacer("emitir",{**p,"conceptos":[{"servicio":1,"cantidad":2}]})[0],400)
        cobro={"factura":f["id"],"referencia":"REF-01","importe":5000}
        with ThreadPoolExecutor(2) as pool:
            pagos=list(pool.map(lambda _:hacer("pago",cobro)[1],range(2)))
        self.assertCountEqual([r["pago_duplicado"] for r in pagos],[False,True])
        self.assertEqual([r["saldo"] for r in pagos],[6760,6760])

    def test_limite_de_intentos_concurrentes(self):
        with ThreadPoolExecutor(6) as pool:
            resultados=list(pool.map(lambda _:self.peticion("entrar",{"usuario":"operador","clave":"incorrecta"})[0],range(12)))
        self.assertEqual(resultados.count(401),10)
        self.assertEqual(resultados.count(429),2)

    def test_origen_tipo_cookie_y_vencimiento(self):
        import time
        def intercambiar(cabeceras, cuerpo=b"{}"):
            peticion=b"POST /api/inicio HTTP/1.0\r\n"+cabeceras.encode()+b"\r\n\r\n"+cuerpo
            canal=CanalEnMemoria(peticion)
            Peticion(canal,("127.0.0.1",0),self.s)
            return int(canal.salida.getvalue().split()[1])
        host="Host: 127.0.0.1:"+str(self.s.server_port)
        origen="Origin: "+self.s.origen
        tipo="Content-Type: application/json"
        def cab(*partes):return "\r\n".join(partes)
        self.assertEqual(intercambiar(cab(host, "Origin: https://otra.invalid", tipo, "Content-Length: 2")),403)
        self.assertEqual(intercambiar(cab("Host: otro.invalid", origen, tipo, "Content-Length: 2")),403)
        self.assertEqual(intercambiar(cab(host, origen, "Content-Type: text/plain","Content-Length: 2")),415)
        self.assertEqual(intercambiar(cab(host, origen, tipo, "Content-Length: 32769")),413)
        _,_,cookie=self.peticion("entrar",{"usuario":"operador","clave":self.s.clave("operador")})
        self.assertIn("HttpOnly",cookie)
        self.assertIn("SameSite=Strict",cookie)
        sid=self.tokens["operador"].split("=",1)[1]
        self.s.sesiones[sid]=("operador",time.monotonic()-1)
        self.assertEqual(self.peticion("inicio",{},"operador")[0],401)
