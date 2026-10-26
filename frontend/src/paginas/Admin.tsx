import { useEffect, useState } from "react";
import { api } from "../api";

export default function Admin() {
  const [metricas, setMetricas] = useState<any>(null);
  const [verif, setVerif] = useState<any>(null);
  const [reglas, setReglas] = useState<any>(null);
  const [decisiones, setDecisiones] = useState<any[]>([]);
  const [docs, setDocs] = useState<any[]>([]);

  useEffect(() => {
    api("/api/admin/metricas").then(setMetricas);
    api("/api/admin/reglas").then(setReglas);
    api<any[]>("/api/admin/bitacora/decisiones?limite=8").then(setDecisiones);
    api<any[]>("/api/admin/conocimiento").then(setDocs);
  }, []);

  const verificar = () => api("/api/admin/bitacora/verificacion").then(setVerif);
  const nombres: Record<string, string> = { C0: "Acompañamiento", C1: "Monitoreo", C2: "Derivación ordinaria", C3: "Escalamiento prioritario" };

  return (
    <div className="admin">
      <section className="tarjeta">
        <h3>Evaluaciones de los últimos {metricas?.periodo_dias ?? 30} días</h3>
        <div className="kpis">
          {metricas && Object.entries(metricas.evaluaciones_por_categoria).map(([c, n]) => (
            <div key={c} className={`kpi kpi-${c.toLowerCase()}`}><span>{String(n)}</span><small>{c} · {nombres[c]}</small></div>
          ))}
        </div>
        <p className="tenue">Los conteos menores que {metricas?.umbral_k} se muestran como «&lt;{metricas?.umbral_k}» para evitar la reidentificación.</p>
      </section>

      <section className="tarjeta">
        <div className="fila-entre"><h3>Integridad de las bitácoras</h3><button className="btn-primario" onClick={verificar}>Verificar cadena de hashes</button></div>
        {verif && (["decisiones", "accesos"] as const).map((k) => (
          <p key={k} className={verif[k].integra ? "ok" : "error"}>
            {verif[k].integra ? "✔" : "✖"} Bitácora de {k}: {verif[k].registros} registros {verif[k].integra ? "íntegros" : `— falla en el registro ${verif[k].falla_en_id}: ${verif[k].motivo}`}
            {verif[k].ultimo_hash && <code className="hash"> último hash {verif[k].ultimo_hash.slice(0, 20)}…</code>}
          </p>
        ))}
        <table>
          <thead><tr><th>#</th><th>Fecha (UTC)</th><th>Origen</th><th>Categoría</th><th>Acción</th><th>Regla</th><th>Versión</th><th>Hash</th></tr></thead>
          <tbody>{decisiones.map((d) => (
            <tr key={d.id}><td>{d.id}</td><td>{d.registrado_en.slice(0, 19).replace("T", " ")}</td><td>{d.origen}</td><td>{d.categoria}</td><td>{d.accion}</td><td>{d.regla}</td><td>{d.version_reglas}</td><td><code>{d.hash}</code></td></tr>
          ))}</tbody>
        </table>
      </section>

      <section className="tarjeta">
        <h3>Reglas vigentes {reglas && <small className="tenue">v{reglas.version} · huella {reglas.huella.slice(0, 16)}… · proveedor IA: {reglas.proveedor_ia}</small>}</h3>
        <table>
          <thead><tr><th>Regla</th><th>Nombre</th><th>Categoría</th><th>Acción</th><th>Fuentes</th></tr></thead>
          <tbody>{reglas?.reglas.map((r: any) => (
            <tr key={r.id}><td>{r.id}</td><td>{r.nombre}</td><td>{r.categoria}</td><td>{r.accion}</td><td className="tenue">{r.fuentes.join("; ")}</td></tr>
          ))}</tbody>
        </table>
      </section>

      <section className="tarjeta">
        <h3>Base de conocimiento ({docs.length} documentos)</h3>
        <table>
          <thead><tr><th>Documento</th><th>Tema</th><th>Referencia</th><th>Fragmentos</th></tr></thead>
          <tbody>{docs.map((d) => <tr key={d.clave}><td>{d.titulo}</td><td>{d.tema}</td><td className="tenue">{d.referencia}</td><td>{d.fragmentos}</td></tr>)}</tbody>
        </table>
      </section>
    </div>
  );
}
