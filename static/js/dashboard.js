fetch("/api/dashboard").then(r=>r.json()).then(data=>{
const dark=document.documentElement.getAttribute("data-theme")==="dark";
const text=dark?"#ffffff":"#111827"; const grid=dark?"#263449":"#dbe2ef";
new Chart(document.getElementById("movChart"),{type:"line",data:{labels:data.dias,datasets:[{label:"Entradas",data:data.entradas,borderColor:"#22c55e",backgroundColor:"rgba(34,197,94,.12)",tension:.35,fill:true},{label:"Saídas",data:data.saidas,borderColor:"#ef4444",backgroundColor:"rgba(239,68,68,.12)",tension:.35,fill:true}]},options:{responsive:true,plugins:{legend:{labels:{color:text}}},scales:{x:{ticks:{color:text},grid:{color:grid}},y:{ticks:{color:text},grid:{color:grid}}}}});
new Chart(document.getElementById("vendidosChart"),{type:"bar",data:{labels:data.vendidos_labels,datasets:[{label:"Quantidade",data:data.vendidos_valores,backgroundColor:"#8b5cf6"}]},options:{responsive:true,plugins:{legend:{labels:{color:text}}},scales:{x:{ticks:{color:text},grid:{color:grid}},y:{ticks:{color:text},grid:{color:grid}}}}});
});
