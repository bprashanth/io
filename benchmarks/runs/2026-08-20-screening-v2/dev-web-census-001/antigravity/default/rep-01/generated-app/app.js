// 2011 Census Official Data for Patna, Gaya, and Nalanda
const censusData = {
  census_year: 2011,
  census_authority: "Office of the Registrar General & Census Commissioner, Ministry of Home Affairs, Government of India",
  state: "Bihar",
  districts: [
    {
      id: "patna",
      name: "Patna",
      hindi_name: "पटना",
      headquarters: "Patna",
      census_code: "230",
      total_population: 5838465,
      male_population: 3078512,
      female_population: 2759953,
      sex_ratio: 897,
      area_sq_km: 3202,
      density_per_sq_km: 1823,
      overall_literacy_rate: 70.68,
      male_literacy_rate: 78.48,
      female_literacy_rate: 61.96,
      rural_population: 3323875,
      urban_population: 2514590,
      urban_percentage: 43.07,
      rural_percentage: 56.93,
      population_rank_in_state: 1,
      theme_color: "#3b82f6",
      source_name: "Patna DCHB 2011 (PCA XII-B) & patna.nic.in",
      source_link: "https://censusindia.gov.in/nada/index.php/catalog/32832"
    },
    {
      id: "gaya",
      name: "Gaya",
      hindi_name: "गया",
      headquarters: "Gaya",
      census_code: "240",
      total_population: 4391418,
      male_population: 2266566,
      female_population: 2124852,
      sex_ratio: 937,
      area_sq_km: 4976,
      density_per_sq_km: 883,
      overall_literacy_rate: 63.67,
      male_literacy_rate: 73.31,
      female_literacy_rate: 53.34,
      rural_population: 3809817,
      urban_population: 581601,
      urban_percentage: 13.24,
      rural_percentage: 86.76,
      population_rank_in_state: 3,
      theme_color: "#10b981",
      source_name: "Gaya DCHB 2011 (PCA XII-B) & gaya.nic.in",
      source_link: "https://gaya.nic.in/demography/"
    },
    {
      id: "nalanda",
      name: "Nalanda",
      hindi_name: "नालंदा",
      headquarters: "Bihar Sharif",
      census_code: "231",
      total_population: 2877653,
      male_population: 1497060,
      female_population: 1380593,
      sex_ratio: 922,
      area_sq_km: 2355,
      density_per_sq_km: 1222,
      overall_literacy_rate: 64.43,
      male_literacy_rate: 74.86,
      female_literacy_rate: 53.10,
      rural_population: 2419759,
      urban_population: 457894,
      urban_percentage: 15.91,
      rural_percentage: 84.09,
      population_rank_in_state: 11,
      theme_color: "#f59e0b",
      source_name: "Nalanda DCHB 2011 (PCA XII-B) & nalanda.nic.in",
      source_link: "https://nalanda.nic.in/demography/"
    }
  ]
};

// Format numbers in Indian numbering system (e.g. 58,38,465) & standard comma
function formatNumber(num, useIndian = true) {
  if (useIndian) {
    return num.toLocaleString('en-IN');
  }
  return num.toLocaleString();
}

// Calculate percentages
const totalCombined = censusData.districts.reduce((acc, d) => acc + d.total_population, 0);

// Initialize charts
let popChartInstance = null;
let ruralUrbanChartInstance = null;
let shareChartInstance = null;
let literacyChartInstance = null;

function renderCharts() {
  if (typeof Chart === 'undefined') {
    console.warn("Chart.js not loaded, fallback will be used.");
    return;
  }

  const districtNames = censusData.districts.map(d => d.name);
  const totalPops = censusData.districts.map(d => d.total_population);
  const malePops = censusData.districts.map(d => d.male_population);
  const femalePops = censusData.districts.map(d => d.female_population);
  const ruralPops = censusData.districts.map(d => d.rural_population);
  const urbanPops = censusData.districts.map(d => d.urban_population);
  const literacyRates = censusData.districts.map(d => d.overall_literacy_rate);
  const sexRatios = censusData.districts.map(d => d.sex_ratio);

  // 1. Population Overview Chart
  const ctxPop = document.getElementById('populationChart')?.getContext('2d');
  if (ctxPop) {
    if (popChartInstance) popChartInstance.destroy();
    popChartInstance = new Chart(ctxPop, {
      type: 'bar',
      data: {
        labels: districtNames,
        datasets: [
          {
            label: 'Total Population',
            data: totalPops,
            backgroundColor: ['rgba(59, 130, 246, 0.85)', 'rgba(16, 185, 129, 0.85)', 'rgba(245, 158, 11, 0.85)'],
            borderColor: ['#3b82f6', '#10b981', '#f59e0b'],
            borderWidth: 1.5,
            borderRadius: 6
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => ` Population: ${formatNumber(ctx.raw)} (${((ctx.raw / totalCombined) * 100).toFixed(1)}% of 3-District Total)`
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              callback: (val) => (val / 1000000).toFixed(1) + 'M',
              color: '#9ca3af'
            },
            grid: { color: 'rgba(255, 255, 255, 0.05)' }
          },
          x: {
            ticks: { color: '#f3f4f6', font: { weight: '600' } },
            grid: { display: false }
          }
        }
      }
    });
  }

  // 2. Population Share Doughnut
  const ctxShare = document.getElementById('shareChart')?.getContext('2d');
  if (ctxShare) {
    if (shareChartInstance) shareChartInstance.destroy();
    shareChartInstance = new Chart(ctxShare, {
      type: 'doughnut',
      data: {
        labels: districtNames,
        datasets: [{
          data: totalPops,
          backgroundColor: ['#3b82f6', '#10b981', '#f59e0b'],
          borderColor: '#111827',
          borderWidth: 3,
          hoverOffset: 8
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: { color: '#9ca3af', boxWidth: 14, padding: 16 }
          },
          tooltip: {
            callbacks: {
              label: (ctx) => ` ${ctx.label}: ${formatNumber(ctx.raw)} (${((ctx.raw / totalCombined) * 100).toFixed(1)}%)`
            }
          }
        },
        cutout: '68%'
      }
    });
  }

  // 3. Rural vs Urban Split Grouped Bar
  const ctxRuralUrban = document.getElementById('ruralUrbanChart')?.getContext('2d');
  if (ctxRuralUrban) {
    if (ruralUrbanChartInstance) ruralUrbanChartInstance.destroy();
    ruralUrbanChartInstance = new Chart(ctxRuralUrban, {
      type: 'bar',
      data: {
        labels: districtNames,
        datasets: [
          {
            label: 'Rural Population',
            data: ruralPops,
            backgroundColor: 'rgba(16, 185, 129, 0.8)',
            borderColor: '#10b981',
            borderWidth: 1,
            borderRadius: 4
          },
          {
            label: 'Urban Population',
            data: urbanPops,
            backgroundColor: 'rgba(99, 102, 241, 0.8)',
            borderColor: '#6366f1',
            borderWidth: 1,
            borderRadius: 4
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'top',
            labels: { color: '#9ca3af', boxWidth: 12 }
          },
          tooltip: {
            callbacks: {
              label: (ctx) => ` ${ctx.dataset.label}: ${formatNumber(ctx.raw)}`
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              callback: (val) => (val / 1000000).toFixed(1) + 'M',
              color: '#9ca3af'
            },
            grid: { color: 'rgba(255, 255, 255, 0.05)' }
          },
          x: {
            ticks: { color: '#f3f4f6' },
            grid: { display: false }
          }
        }
      }
    });
  }

  // 4. Literacy & Demographics
  const ctxLit = document.getElementById('literacyChart')?.getContext('2d');
  if (ctxLit) {
    if (literacyChartInstance) literacyChartInstance.destroy();
    literacyChartInstance = new Chart(ctxLit, {
      type: 'bar',
      data: {
        labels: districtNames,
        datasets: [
          {
            label: 'Male Literacy (%)',
            data: censusData.districts.map(d => d.male_literacy_rate),
            backgroundColor: 'rgba(59, 130, 246, 0.75)',
            borderRadius: 4
          },
          {
            label: 'Female Literacy (%)',
            data: censusData.districts.map(d => d.female_literacy_rate),
            backgroundColor: 'rgba(236, 72, 153, 0.75)',
            borderRadius: 4
          },
          {
            label: 'Overall Literacy (%)',
            data: literacyRates,
            backgroundColor: 'rgba(16, 185, 129, 0.75)',
            borderRadius: 4
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'top',
            labels: { color: '#9ca3af', boxWidth: 12 }
          },
          tooltip: {
            callbacks: {
              label: (ctx) => ` ${ctx.dataset.label}: ${ctx.raw}%`
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            max: 100,
            ticks: {
              callback: (val) => val + '%',
              color: '#9ca3af'
            },
            grid: { color: 'rgba(255, 255, 255, 0.05)' }
          },
          x: {
            ticks: { color: '#f3f4f6' },
            grid: { display: false }
          }
        }
      }
    });
  }
}

// Toggle Theme
function toggleTheme() {
  const currentTheme = document.documentElement.getAttribute('data-theme');
  const targetTheme = currentTheme === 'light' ? 'dark' : 'light';
  document.documentElement.setAttribute('data-theme', targetTheme);
  localStorage.setItem('theme', targetTheme);
  const themeBtn = document.getElementById('themeToggleBtn');
  if (themeBtn) {
    themeBtn.innerHTML = targetTheme === 'light' ? '🌙 Dark Mode' : '☀️ Light Mode';
  }
  renderCharts();
}

// Initialize on DOM Ready
document.addEventListener('DOMContentLoaded', () => {
  const savedTheme = localStorage.getItem('theme') || 'dark';
  document.documentElement.setAttribute('data-theme', savedTheme);
  const themeBtn = document.getElementById('themeToggleBtn');
  if (themeBtn) {
    themeBtn.innerHTML = savedTheme === 'light' ? '🌙 Dark Mode' : '☀️ Light Mode';
    themeBtn.addEventListener('click', toggleTheme);
  }

  renderCharts();
});

// CSV Download Handler
function downloadCSV() {
  const csvContent = "data:text/csv;charset=utf-8," + 
    "District,Exact Population,Population (in Lakh),Census Year,Male Population,Female Population,Sex Ratio,Literacy Rate (%),Area (sq km),Density (/sq km),Source URL\n" +
    censusData.districts.map(d => 
      `"${d.name}",${d.total_population},${(d.total_population/100000).toFixed(2)},${censusData.census_year},${d.male_population},${d.female_population},${d.sex_ratio},${d.overall_literacy_rate},${d.area_sq_km},${d.density_per_sq_km},"${d.source_link}"`
    ).join("\n");

  const encodedUri = encodeURI(csvContent);
  const link = document.createElement("a");
  link.setAttribute("href", encodedUri);
  link.setAttribute("download", "bihar_census_2011_patna_gaya_nalanda.csv");
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

document.addEventListener('DOMContentLoaded', () => {
  const dlBtn = document.getElementById('downloadCsvBtn');
  if (dlBtn) {
    dlBtn.addEventListener('click', downloadCSV);
  }
});
