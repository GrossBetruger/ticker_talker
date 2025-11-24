let priceChart = null;

// Set default end date to today
document.addEventListener('DOMContentLoaded', function() {
    const endDateInput = document.getElementById('end-date');
    const startDateInput = document.getElementById('start-date');
    
    if (endDateInput) {
        const today = new Date().toISOString().split('T')[0];
        endDateInput.value = today;
        endDateInput.max = today;
    }
    
    if (startDateInput) {
        const oneYearAgo = new Date();
        oneYearAgo.setFullYear(oneYearAgo.getFullYear() - 1);
        startDateInput.value = oneYearAgo.toISOString().split('T')[0];
        startDateInput.max = new Date().toISOString().split('T')[0];
    }
    
    // Handle time window toggle
    const timeWindowRadios = document.querySelectorAll('input[name="timeWindow"]');
    const periodGroup = document.getElementById('period-group');
    const datesGroup = document.getElementById('dates-group');
    
    timeWindowRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.value === 'period') {
                periodGroup.style.display = 'block';
                datesGroup.style.display = 'none';
            } else {
                periodGroup.style.display = 'none';
                datesGroup.style.display = 'block';
            }
        });
    });
    
    // Handle compare button click
    const compareBtn = document.getElementById('compare-btn');
    compareBtn.addEventListener('click', handleCompare);
});

async function handleCompare() {
    const tickersInput = document.getElementById('tickers').value.trim();
    const timeWindowType = document.querySelector('input[name="timeWindow"]:checked').value;
    const compareBtn = document.getElementById('compare-btn');
    const btnText = compareBtn.querySelector('.btn-text');
    const btnLoader = compareBtn.querySelector('.btn-loader');
    const errorMessage = document.getElementById('error-message');
    const chartContainer = document.getElementById('chart-container');
    const summaryContainer = document.getElementById('summary-container');
    
    // Hide previous results and errors
    errorMessage.style.display = 'none';
    chartContainer.style.display = 'none';
    summaryContainer.style.display = 'none';
    
    if (!tickersInput) {
        showError('Please enter at least one ticker symbol');
        return;
    }
    
    // Prepare request data
    const requestData = {
        tickers: tickersInput,
        time_window_type: timeWindowType
    };
    
    if (timeWindowType === 'dates') {
        const startDate = document.getElementById('start-date').value;
        const endDate = document.getElementById('end-date').value;
        
        if (!startDate || !endDate) {
            showError('Please select both start and end dates');
            return;
        }
        
        if (new Date(startDate) >= new Date(endDate)) {
            showError('Start date must be before end date');
            return;
        }
        
        requestData.start_date = startDate;
        requestData.end_date = endDate;
    } else {
        requestData.period = document.getElementById('period').value;
    }
    
    // Show loading state
    compareBtn.disabled = true;
    btnText.style.display = 'none';
    btnLoader.style.display = 'inline';
    
    try {
        const response = await fetch('/api/compare', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'An error occurred');
        }
        
        // Display results
        displayChart(data.chart_data, data.start_date, data.end_date);
        displaySummary(data.summary);
        
        chartContainer.style.display = 'block';
        summaryContainer.style.display = 'block';
        
    } catch (error) {
        showError(error.message);
    } finally {
        // Reset button state
        compareBtn.disabled = false;
        btnText.style.display = 'inline';
        btnLoader.style.display = 'none';
    }
}

function displayChart(chartData, startDate, endDate) {
    const canvas = document.getElementById('price-chart');
    const ctx = canvas.getContext('2d');
    
    // Destroy existing chart if it exists
    if (priceChart) {
        priceChart.destroy();
    }
    
    priceChart = new Chart(ctx, {
        type: 'line',
        data: chartData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: `Normalized Price Comparison (${startDate} to ${endDate})`,
                    font: {
                        size: 18,
                        weight: 'bold'
                    },
                    padding: {
                        top: 10,
                        bottom: 20
                    }
                },
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 15,
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + context.parsed.y.toFixed(2) + '%';
                        }
                    }
                }
            },
            scales: {
                x: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Date',
                        font: {
                            size: 14,
                            weight: 'bold'
                        }
                    },
                    ticks: {
                        maxRotation: 45,
                        minRotation: 45
                    }
                },
                y: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Normalized Price (%)',
                        font: {
                            size: 14,
                            weight: 'bold'
                        }
                    },
                    grid: {
                        color: function(context) {
                            if (context.tick.value === 100) {
                                return 'rgba(0, 0, 0, 0.3)';
                            }
                            return 'rgba(0, 0, 0, 0.1)';
                        },
                        lineWidth: function(context) {
                            if (context.tick.value === 100) {
                                return 2;
                            }
                            return 1;
                        }
                    },
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                }
            },
            elements: {
                point: {
                    radius: 0,
                    hoverRadius: 5
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
}

function displaySummary(summary) {
    const summaryContent = document.getElementById('summary-content');
    summaryContent.innerHTML = '';
    
    const grid = document.createElement('div');
    grid.className = 'summary-grid';
    
    for (const [ticker, stats] of Object.entries(summary)) {
        const card = document.createElement('div');
        card.className = 'summary-card';
        
        card.innerHTML = `
            <h3>${ticker}</h3>
            <div class="summary-stat">
                <span class="summary-stat-label">Starting Price:</span>
                <span class="summary-stat-value">$${stats.start_price.toFixed(2)}</span>
            </div>
            <div class="summary-stat">
                <span class="summary-stat-label">Ending Price:</span>
                <span class="summary-stat-value">$${stats.end_price.toFixed(2)}</span>
            </div>
            <div class="summary-stat">
                <span class="summary-stat-label">Normalized Start:</span>
                <span class="summary-stat-value">${stats.start_normalized.toFixed(2)}%</span>
            </div>
            <div class="summary-stat">
                <span class="summary-stat-label">Normalized End:</span>
                <span class="summary-stat-value">${stats.end_normalized.toFixed(2)}%</span>
            </div>
            <div class="summary-stat">
                <span class="summary-stat-label">Change:</span>
                <span class="summary-stat-value ${stats.change_pct >= 0 ? 'positive' : 'negative'}">
                    ${stats.change_pct >= 0 ? '+' : ''}${stats.change_pct.toFixed(2)}%
                </span>
            </div>
            <div class="summary-stat">
                <span class="summary-stat-label">Actual Return:</span>
                <span class="summary-stat-value ${stats.actual_return >= 0 ? 'positive' : 'negative'}">
                    ${stats.actual_return >= 0 ? '+' : ''}${stats.actual_return.toFixed(2)}%
                </span>
            </div>
        `;
        
        grid.appendChild(card);
    }
    
    summaryContent.appendChild(grid);
}

function showError(message) {
    const errorMessage = document.getElementById('error-message');
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
}

