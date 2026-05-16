
const tipoMov = document.getElementById("tipoMov");
const motivoMov = document.getElementById("motivoMov");

function carregarMotivos(){
    if(!tipoMov || !motivoMov) return;

    motivoMov.innerHTML = "";

    let motivos = [];

    if(tipoMov.value === "entrada"){
        motivos = [
            "Compra de Fornecedor",
            "Devolução de Cliente"
        ];
    } else {
        motivos = [
            "Venda",
            "Produto Defeituoso",
            "Uso Interno"
        ];
    }

    motivos.forEach(m => {
        const opt = document.createElement("option");
        opt.value = m;
        opt.textContent = m;
        motivoMov.appendChild(opt);
    });
}

if(tipoMov){
    carregarMotivos();
    tipoMov.addEventListener("change", carregarMotivos);
}
