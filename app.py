import base64
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Calculadora TRM",
    page_icon="favicon.ico",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def file_to_base64(path: str):
    file_path = Path(path)
    if not file_path.exists():
        return None
    return base64.b64encode(file_path.read_bytes()).decode("utf-8")


def money(value):
    if value is None:
        return "—"
    text = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"$ {text}"


def num(value):
    if value is None:
        return "—"
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def safe_div(a, b):
    if a is None or b is None or b == 0:
        return None
    return a / b


def abs_diff(a, b):
    if a is None or b is None:
        return None
    return abs(a - b)


def limpiar_si_cambia_modo(modo_actual):
    if "modo_anterior" not in st.session_state:
        st.session_state.modo_anterior = modo_actual
    if st.session_state.modo_anterior != modo_actual:
        for key in [
            "trm", "unidad_sap", "valor_material_sap", "valor_unitario_fv",
            "valor_total_fv_factura", "unidad_medida", "cantidad_total_fv",
        ]:
            st.session_state[key] = None
        st.session_state.modo_anterior = modo_actual
        st.rerun()


def detectar_caso(modo, trm, unidad_sap, valor_material_sap, valor_unitario_fv, unidad_medida):
    """
    Casos disponibles:
    1. Factura por KG:
       FV/TRM coincide con SAP. Cantidad FV se ingresa en KG.
    2. Factura por unidad/caneca y SAP por KG:
       FV/TRM da valor por caneca; se divide entre la unidad de medida.
       Ejemplo: 254.363,20 / 3.633,76 = 70 USD/caneca; 70 / 20 = 3,50 USD/KG.
    3. Factura por unidad directa:
       Factura y SAP manejan la misma unidad.
    """
    valor_usd_factura = safe_div(valor_unitario_fv, trm)
    if valor_usd_factura is None:
        return "pendiente", "Complete los campos requeridos.", None, None

    if modo == "Factura por KG":
        return "kg", "Factura por KG: el valor unitario FV ya viene por KG.", valor_usd_factura, safe_div(valor_usd_factura, unidad_sap)

    if modo == "Factura por caneca y SAP por KG":
        return "caneca_sap_kg", "Factura por caneca y SAP por KG: FV/TRM da el valor USD por caneca; luego se divide entre los KG de la caneca.", valor_usd_factura, safe_div(valor_usd_factura, unidad_medida)

    if modo == "Unitario directo":
        return "unidad_directa", "Unitario directo: FV/TRM valida contra SAP y calcula el valor por estiba con la unidad de medida.", valor_usd_factura, safe_div(valor_usd_factura, unidad_sap)

    return "pendiente", "Seleccione un tipo de validación válido.", valor_usd_factura, None


def calcular(modo, trm, unidad_sap, valor_material_sap, valor_unitario_fv, valor_total_fv_factura, unidad_medida, cantidad_total_fv):
    caso, descripcion, valor_usd_factura, validacion_sap = detectar_caso(
        modo, trm, unidad_sap, valor_material_sap, valor_unitario_fv, unidad_medida
    )

    cantidad_a_recibir = None
    valor_unitario_calculado = None
    valor_total_calculado = None
    etiqueta_cantidad = "Cantidad a recibir"
    instruccion_cantidad = ""

    if cantidad_total_fv is not None and valor_unitario_fv is not None:
        if caso == "kg":
            # La factura viene en KG. Cantidad FV = KG.
            cantidad_a_recibir = safe_div(cantidad_total_fv, unidad_medida)
            valor_unitario_calculado = valor_unitario_fv
            valor_total_calculado = cantidad_total_fv * valor_unitario_fv
            etiqueta_cantidad = "Cantidad a recibir / unidades"
            instruccion_cantidad = "Ingrese la cantidad total FV en KG. El sistema divide por la unidad de medida para obtener las unidades/canecas."

        elif caso == "caneca_sap_kg":
            # La factura viene por caneca/unidad. Cantidad FV = canecas/unidades.
            cantidad_a_recibir = cantidad_total_fv * unidad_medida if unidad_medida is not None else None
            valor_unitario_calculado = valor_unitario_fv
            valor_total_calculado = cantidad_total_fv * valor_unitario_fv
            etiqueta_cantidad = "Cantidad total en KG"
            instruccion_cantidad = "Ingrese la cantidad total FV en canecas. Ejemplo: si la factura trae 234 canecas, ingrese 234; el sistema multiplica por los KG de la caneca."

        elif caso == "unidad_directa":
            # Unitario directo con conversión por unidad SAP.
            # Ejemplo LATA:
            # Valor unitario FV / TRM = valor SAP.
            # Valor por estiba = (valor unitario FV * unidad_medida) / unidad_sap.
            # Total = cantidad FV * valor por estiba.
            cantidad_a_recibir = cantidad_total_fv
            valor_unitario_calculado = (
                safe_div(valor_unitario_fv * unidad_medida, unidad_sap)
                if unidad_medida is not None and unidad_sap is not None
                else None
            )
            valor_total_calculado = (
                cantidad_total_fv * valor_unitario_calculado
                if valor_unitario_calculado is not None
                else None
            )
            etiqueta_cantidad = "Cantidad a recibir"
            instruccion_cantidad = "Ingrese la cantidad total FV en la misma unidad de la factura."

    diferencia = None
    if valor_total_fv_factura is not None and valor_total_calculado is not None:
        diferencia = valor_total_fv_factura - valor_total_calculado

    return {
        "caso": caso,
        "descripcion": descripcion,
        "valor_usd_factura": valor_usd_factura,
        "validacion_sap": validacion_sap,
        "cantidad_a_recibir": cantidad_a_recibir,
        "valor_unitario_calculado": valor_unitario_calculado,
        "valor_total_calculado": valor_total_calculado,
        "diferencia": diferencia,
        "etiqueta_cantidad": etiqueta_cantidad,
        "instruccion_cantidad": instruccion_cantidad,
    }


logo_b64 = file_to_base64("favicon.ico")
logo_html = f'<img src="data:image/x-icon;base64,{logo_b64}" class="logo-img" alt="Logo">' if logo_b64 else '<div class="logo-fallback">TRM</div>'

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
:root{--azul:#002f8f;--azul2:#0047c7;--oscuro:#06173f;--borde:#d5deea;--verde:#027a48;--verdebg:#ecfdf3;}
html,body,[class*="css"]{font-family:'Inter',sans-serif}.stApp{background:#fff;border-top:7px solid var(--azul)}.block-container{max-width:1120px;padding-top:2.5rem!important;padding-bottom:1rem!important}.main-shell{
background:#fff;
border-bottom:1px solid var(--borde);
box-shadow:0 10px 26px rgba(15,23,42,.05);
margin-bottom:18px;
overflow:visible!important;
position:relative;
z-index:1;
}.topbar{
min-height:96px!important;
display:flex;
align-items:center;
justify-content:space-between;
padding:22px 38px 18px 38px!important;
gap:24px;
flex-wrap:nowrap;
overflow:visible!important;
}.brand{display:flex;align-items:center;gap:16px;min-width:0;overflow:visible!important}.logo-img,.logo-fallback{width:48px;height:48px;object-fit:contain}.logo-fallback{border-radius:50%;border:3px solid var(--azul);color:var(--azul);display:flex;align-items:center;justify-content:center;font-weight:900;font-size:.7rem}.brand-divider{width:1px;height:40px;background:var(--borde)}.brand-title{font-size:1.12rem;font-weight:900;color:var(--oscuro)}.brand-subtitle{color:#334155;font-size:.75rem;margin-top:5px;font-weight:700}.status{background:var(--verdebg);color:var(--verde);border:1px solid #86efac;padding:9px 18px!important;border-radius:999px;font-size:.76rem;font-weight:900;line-height:1.2;white-space:nowrap;display:flex;align-items:center;justify-content:center;min-height:34px;overflow:visible!important}.section-title{font-size:.78rem;font-weight:900;letter-spacing:.13em;text-transform:uppercase;color:var(--azul);margin-bottom:18px}div[data-testid="stVerticalBlockBorderWrapper"]{border:1px solid var(--borde)!important;border-radius:16px!important;background:#fff!important;box-shadow:0 4px 12px rgba(15,23,42,.025);padding:16px!important}div[data-testid="stRadio"] p,div[data-testid="stRadio"] label,div[data-testid="stNumberInput"] label{font-weight:800!important;color:var(--oscuro)!important}div[data-testid="stNumberInput"] input{border-radius:9px!important;border:1px solid #c7d3e3!important;min-height:42px;color:var(--azul)!important;font-weight:900!important;font-size:.92rem!important}.trm-help,.case-box{margin-top:18px;border:1px solid #c7d3e3;background:#f3f7ff;border-radius:12px;padding:18px 20px;font-size:.86rem;line-height:1.55;color:var(--oscuro)}.trm-help-title{color:var(--azul);font-size:.78rem;font-weight:900;text-transform:uppercase;letter-spacing:.13em;margin-bottom:7px}.results{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px}.metric{border:1px solid #cfd8e6;background:#fff;border-radius:10px;padding:14px;min-height:76px;display:flex;flex-direction:column;justify-content:center;align-items:center;box-shadow:0 3px 8px rgba(15,23,42,.035)}.metric.ok{background:linear-gradient(180deg,#ecfdf3 0%,#d1fadf 100%);border:1px solid #86efac}.metric-label{color:var(--oscuro);font-size:.70rem;font-weight:900;text-align:center;margin-bottom:10px}.metric-value{color:var(--oscuro);font-size:1.12rem;font-weight:900;letter-spacing:-.04em}.result-footer{display:grid;grid-template-columns:1fr 260px;gap:12px;align-items:center;margin-top:14px}.validation-ok,.validation-warn,.empty-note-box{border-radius:9px;padding:13px 16px;font-weight:800;font-size:.86rem}.validation-ok,.empty-note-box{background:var(--verdebg);border:1px solid #86efac;color:var(--verde)}.validation-warn{background:#eef5ff;border:1px solid #9cc2ff;color:#0b3b86}.print-card{display:none}button[kind="primary"]{background:var(--azul)!important;border:1px solid var(--azul)!important;border-radius:9px!important;min-height:44px!important;font-weight:900!important}.footer{text-align:center;color:#94a3b8;font-size:.75rem;padding:10px}@media(max-width:900px){.results{grid-template-columns:repeat(2,minmax(0,1fr))}.result-footer{grid-template-columns:1fr}}@media(max-width:560px){.results{grid-template-columns:1fr}.topbar{height:auto;padding:16px;flex-direction:column;align-items:flex-start;gap:12px}.brand-divider{display:none}}@media print{
@page{
size:letter portrait;
margin:5mm;
}

html,body{
zoom:0.88;
}

header,
.stToolbar,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
.stButton,
.no-print{
display:none!important;
}

.stApp{
background:#fff!important;
border-top:none!important;
}

.block-container{
max-width:100%!important;
padding:0!important;
margin:0!important;
}

.main-shell,
div[data-testid="stVerticalBlockBorderWrapper"],
.metric,
.validation-ok,
.validation-warn,
.print-card,
.case-box{
box-shadow:none!important;
break-inside:avoid!important;
page-break-inside:avoid!important;
}

.main-shell{
margin-bottom:4px!important;
}

.topbar{
min-height:42px!important;
padding:6px 10px!important;
gap:10px!important;
flex-wrap:nowrap!important;
overflow:visible!important;
}

.logo-img,
.logo-fallback{
width:28px!important;
height:28px!important;
min-width:28px!important;
min-height:28px!important;
}

.brand-title{
font-size:11px!important;
}

.brand-subtitle,
.status{
font-size:7px!important;
}

.section-title{
font-size:7px!important;
margin-bottom:4px!important;
}

div[data-testid="stVerticalBlockBorderWrapper"]{
padding:5px!important;
margin-bottom:4px!important;
border-radius:8px!important;
}

.trm-help{
display:none!important;
}

div[data-testid="stNumberInput"] label,
div[data-testid="stRadio"] label{
font-size:7px!important;
}

div[data-testid="stNumberInput"] input{
min-height:20px!important;
font-size:7px!important;
padding:1px 4px!important;
}

.results{
grid-template-columns:repeat(5,1fr)!important;
gap:4px!important;
}

.metric{
min-height:48px!important;
padding:5px!important;
border-radius:6px!important;
}

.metric-label{
font-size:5px!important;
margin-bottom:4px!important;
}

.metric-value{
font-size:9px!important;
}

.result-footer{
display:block!important;
margin-top:4px!important;
}

.validation-ok,
.validation-warn,
.empty-note-box,
.case-box{
font-size:7px!important;
padding:5px!important;
margin-top:4px!important;
line-height:1.2!important;
}

.print-card{
display:block!important;
font-size:7px!important;
padding:5px!important;
margin-top:4px!important;
border:1px solid #dbe3ed!important;
border-radius:6px!important;
}

.footer{
font-size:6px!important;
padding:3px!important;
margin-top:2px!important;
}
}
</style>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="main-shell"><div class="topbar"><div class="brand">{logo_html}<div class="brand-divider"></div><div><div class="brand-title">CalculadoraTRM</div><div class="brand-subtitle">Validación financiera SAP / FV</div></div></div><div class="status">✓ Sistema operativo</div></div></div>
""", unsafe_allow_html=True)

with st.container(border=True):
    modo = st.radio(
        "Tipo de validación",
        ["Factura por KG", "Factura por caneca y SAP por KG", "Unitario directo"],
        horizontal=True,
        key="modo",
        help="Seleccione el caso según venga la factura: por KG, por caneca con SAP en KG, o unitario directo.",
    )
limpiar_si_cambia_modo(modo)

with st.container(border=True):
    st.markdown('<div class="section-title">Datos SAP</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        trm = st.number_input("TRM del día de la factura ⓘ", min_value=0.0, value=None, placeholder="Digite TRM", step=0.01, format="%.2f", key="trm")
    with c2:
        unidad_sap = st.number_input("Unidad de medida SAP", min_value=0.0, value=None, placeholder="Digite unidad SAP", step=0.01, format="%.2f", key="unidad_sap")
    with c3:
        valor_material_sap = st.number_input("Valor unidad material SAP", min_value=0.0, value=None, placeholder="Digite valor SAP", step=0.01, format="%.2f", key="valor_material_sap")
    st.markdown("""
<div class="trm-help"><div><div class="trm-help-title">Proceso SAP para obtener la TRM</div>En la transacción <strong>ME21N</strong>, diríjase a <strong>Cabecera &gt; Dat. org.</strong> y registre <strong>Org. compras 5RPC</strong>, <strong>Grupo compras 006</strong> y <strong>Sociedad BA00</strong>.<br>Luego vaya a <strong>Entrega / Factura</strong>, seleccione la <strong>fecha del día</strong>, confirme la <strong>moneda</strong> y presione <strong>Enter</strong>. Finalmente, en <strong>Entrega de factura</strong>, el campo <strong>Tipo de cambio</strong> mostrará la TRM correcta.</div></div>
""", unsafe_allow_html=True)

with st.container(border=True):
    st.markdown('<div class="section-title">Datos de factura</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        valor_unitario_fv = st.number_input("Valor unitario FV", min_value=0.0, value=None, placeholder="Digite valor unitario", step=0.01, format="%.2f", key="valor_unitario_fv", help="Ingrese el valor unitario tal como aparece en la factura.")
    with c2:
        valor_total_fv_factura = st.number_input("Valor total FV factura", min_value=0.0, value=None, placeholder="Digite total factura", step=0.01, format="%.2f", key="valor_total_fv_factura")

# Etiquetas dinamicas para Datos de validacion
if modo == "Factura por KG":
    label_unidad_medida = "KG por unidad / factor de conversión"
    placeholder_unidad_medida = "Ej: 25 si 1 unidad trae 25 KG"
    help_unidad_medida = "Ingrese cuántos KG trae cada unidad/caneca para convertir la cantidad total FV."
    help_cantidad_total = "Ingrese la cantidad total de la factura en KG."

elif modo == "Factura por caneca y SAP por KG":
    label_unidad_medida = "KG por caneca"
    placeholder_unidad_medida = "Ej: 20 si la caneca trae 20 KG"
    help_unidad_medida = "Ingrese los KG que trae cada caneca. Ejemplo: si 1 caneca trae 20 KG, ingrese 20."
    help_cantidad_total = "Ingrese la cantidad de canecas que aparecen en la factura."

else:
    label_unidad_medida = "Unidad de medida"
    placeholder_unidad_medida = "Ej: 7780"
    help_unidad_medida = "Ingrese la unidad de medida usada para calcular el valor por estiba."
    help_cantidad_total = "Ingrese la cantidad total FV en la misma unidad de la factura."


with st.container(border=True):
    st.markdown('<div class="section-title">Datos de validación</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        unidad_medida = st.number_input(label_unidad_medida, min_value=0.0, value=None, placeholder=placeholder_unidad_medida, step=0.01, format="%.2f", key="unidad_medida", help=help_unidad_medida)
    with c2:
        cantidad_total_fv = st.number_input("Cantidad total FV", min_value=0.0, value=None, placeholder="Digite cantidad según factura", step=0.01, format="%.2f", key="cantidad_total_fv", help=help_cantidad_total)

resultado = calcular(modo, trm, unidad_sap, valor_material_sap, valor_unitario_fv, valor_total_fv_factura, unidad_medida, cantidad_total_fv)
validacion_ok = resultado["validacion_sap"] is not None and valor_material_sap is not None and abs(resultado["validacion_sap"] - valor_material_sap) <= 0.01
resultado_ok = resultado["diferencia"] is not None and abs(resultado["diferencia"]) <= 1
clase_primera = "metric ok" if validacion_ok else "metric"

with st.container(border=True):
    st.markdown('<div class="section-title">Resultados calculados</div>', unsafe_allow_html=True)
    regla_html = ""

    if resultado["caso"] == "kg":
        regla_html = "<strong>Regla:</strong> FV/TRM debe coincidir con el valor SAP porque la factura viene por KG."

    elif resultado["caso"] == "caneca_sap_kg":
        regla_html = "<strong>Regla:</strong> si SAP está por KG y la factura por caneca, la validación es (Valor unitario FV / TRM) / KG por caneca."

    elif resultado["caso"] == "unidad_directa":
        regla_html = "<strong>Regla:</strong> FV/TRM debe coincidir directamente con el valor SAP."

    st.markdown(f"""
<div class="case-box">
<strong>Caso:</strong> {resultado['descripcion']}<br>
<strong>Cómo llenar cantidad:</strong> {resultado['instruccion_cantidad'] or 'Complete los campos para ver la instrucción.'}<br>
{regla_html}
</div>
""", unsafe_allow_html=True)
    st.markdown(f"""
<div class="results">
    <div class="{clase_primera}">
        <div class="metric-label">Validación SAP</div>
        <div class="metric-value">
            {num(valor_material_sap if resultado['caso'] == 'unidad_directa' else resultado['validacion_sap'])}
        </div>
    </div>
    <div class="metric"><div class="metric-label">Valor USD factura</div><div class="metric-value">{num(resultado['valor_usd_factura'])}</div></div>
    <div class="metric"><div class="metric-label">{resultado['etiqueta_cantidad']}</div><div class="metric-value">{num(resultado['cantidad_a_recibir'])}</div></div>
    <div class="metric"><div class="metric-label">Valor por estiba</div><div class="metric-value">{money(resultado['valor_unitario_calculado'])}</div></div>
    <div class="metric"><div class="metric-label">Valor total FV calculado</div><div class="metric-value">{money(resultado['valor_total_calculado'])}</div></div>
</div>
""", unsafe_allow_html=True)

    if resultado["diferencia"] is None:
        mensaje_html = '<div class="empty-note-box">✓ Complete los campos requeridos para generar la validación.</div>'
    elif abs(resultado["diferencia"]) <= 1:
        mensaje_html = f'<div class="validation-ok">✓ Perfecto: los valores coinciden. Diferencia: {money(resultado["diferencia"])}</div>'
    elif resultado["diferencia"] > 0:
        mensaje_html = f'<div class="validation-warn">Atención: el cálculo queda por debajo de la factura por {money(resultado["diferencia"])}.</div>'
    else:
        mensaje_html = f'<div class="validation-warn">Atención: el cálculo queda por encima de la factura por {money(abs(resultado["diferencia"]))}.</div>'

    if (
        resultado["caso"] != "unidad_directa"
        and resultado["validacion_sap"] is not None
        and valor_material_sap is not None
        and abs(resultado["validacion_sap"] - valor_material_sap) > 0.01
    ):
        mensaje_html += f'<div class="validation-warn" style="margin-top:8px;">Validación SAP no coincide: SAP = {num(valor_material_sap)} vs calculado = {num(resultado["validacion_sap"])}.</div>'

    st.markdown(f'<div class="result-footer"><div>{mensaje_html}</div><div class="no-print">', unsafe_allow_html=True)
    if st.button("🖨️ Imprimir soporte de validación", type="primary", use_container_width=True):
        components.html("""<script>setTimeout(function(){window.parent.print();},300);</script>""", height=0)
    st.markdown("</div></div>", unsafe_allow_html=True)

    st.markdown(f"""
<div class="print-card"><strong>Soporte de validación</strong><br>Tipo seleccionado: {modo}<br>Caso detectado: {resultado['caso']}<br>TRM: {num(trm)}<br>Valor unitario FV: {money(valor_unitario_fv)}<br>Total factura: {money(valor_total_fv_factura)}<br>Unidad de medida / factor: {num(unidad_medida)}<br>Cantidad FV: {num(cantidad_total_fv)}<br>Validación SAP: {num(resultado['validacion_sap'])}<br>Total calculado: {money(resultado['valor_total_calculado'])}<br>Diferencia: {money(resultado['diferencia'])}</div>
""", unsafe_allow_html=True)

st.markdown('<div class="footer">CalculadoraTRM · Sistema profesional de validación</div>', unsafe_allow_html=True)
