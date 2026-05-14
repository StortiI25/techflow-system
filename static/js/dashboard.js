fetch("/api/dashboard").then(r=>r.json()).then(data=>{
const dark=document.documentElement.getAttribute("data-theme")==="dark";const text=dark?"#f8fafc":"#111827";const grid=dark?"#263449":"#e5e7eb";
new Chart(document.getElementById("salesChart"),{type:"line",data:{labels:data.vendas_labels,datasets:[{label:"Vendas (R$)",data:data.vendas_valores,borderColor:"#7c3aed",backgroundColor:"rgba(124,58,237,.2)",tension:.35,fill:true}]},options:{plugins:{legend:{labels:{color:text}}},scales:{x:{ticks:{color:text},grid:{color:grid}},y:{ticks:{color:text},grid:{color:grid}}}}});
new Chart(document.getElementById("productsChart"),{type:"bar",data:{labels:data.produtos_labels,datasets:[{label:"Quantidade",data:data.produtos_valores,backgroundColor:"#7c3aed"}]},options:{plugins:{legend:{labels:{color:text}}},scales:{x:{ticks:{color:text},grid:{color:grid}},y:{ticks:{color:text},grid:{color:grid}}}}});
});
