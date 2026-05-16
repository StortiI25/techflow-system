const tipo=document.getElementById("tipoMov");
const motivo=document.getElementById("motivoMov");
const barcode=document.getElementById("barcodeInput");
function updateMotivos(){
  const entrada=["Compra de Fornecedor","Devolução de Cliente"];
  const saida=["Venda","Produto Defeituoso","Uso Interno"];
  const lista=tipo.value==="entrada"?entrada:saida;
  motivo.innerHTML=lista.map(m=>`<option value="${m}">${m}</option>`).join("");
}
if(tipo&&motivo){tipo.addEventListener("change",updateMotivos);updateMotivos();}
if(barcode){barcode.addEventListener("keydown",e=>{if(e.key==="Enter"){e.preventDefault();const code=barcode.value.trim();if(code) window.location.href="/produto/codigo/"+encodeURIComponent(code);}});}
