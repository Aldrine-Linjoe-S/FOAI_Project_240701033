Chart.defaults.font.family = 'DM Sans';
document.querySelectorAll('#matchChart').forEach(canvas => {
  new Chart(canvas, {type:'bar', data:{labels:JSON.parse(canvas.dataset.labels),datasets:[{data:JSON.parse(canvas.dataset.values),backgroundColor:['#654ee8','#8492ff','#9ac7ff'],borderRadius:9,maxBarThickness:40}]}, options:{indexAxis:'y',scales:{x:{min:0,max:100,grid:{display:false},ticks:{callback:v=>v+'%'}},y:{grid:{display:false}}},plugins:{legend:{display:false}}}});
});
