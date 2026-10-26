import { useState } from "react";
import { cerrarSesion, leerSesion } from "./api";
import Ingreso from "./paginas/Ingreso";
import Estudiante from "./paginas/Estudiante";
import Atencion from "./paginas/Atencion";
import Admin from "./paginas/Admin";

export default function App() {
  const [sesion, setSesion] = useState(leerSesion());
  const salir = () => { cerrarSesion(); setSesion(null); };

  if (!sesion) return <Ingreso alIngresar={setSesion} />;

  const etiquetaRol: Record<string, string> = {
    ESTUDIANTE: "Estudiante", ATENCION: "Personal de atención psicológica", ADMIN: "Administración técnica",
  };
  return (
    <div className="app">
      <header className="barra">
        <div className="marca">
          <span className="logo" aria-hidden>◆</span>
          <div>
            <strong>SAAC</strong>
            <small>Acompañamiento académico · Ingeniería en Ciencias y Sistemas</small>
          </div>
        </div>
        <div className="usuario">
          <span>{sesion.nombre}<small>{etiquetaRol[sesion.rol]}</small></span>
          <button className="btn-texto" onClick={salir}>Salir</button>
        </div>
      </header>
      {sesion.rol === "ESTUDIANTE" && <Estudiante />}
      {sesion.rol === "ATENCION" && <Atencion />}
      {sesion.rol === "ADMIN" && <Admin />}
    </div>
  );
}
