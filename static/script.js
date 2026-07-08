function renumberLessons() {

    // Renumber timetable
    document.querySelectorAll('#lessonTableBody tr').forEach((row, index) => {
        row.cells[0].textContent = index + 1;
    });

    // Renumber progress table
    document.querySelectorAll('#progressTableBody tr').forEach((row, index) => {
        row.cells[0].textContent = index + 1;
    });

}

// ==========================================
// Window data bridge
// ==========================================
// Reads the real backend values that index.html injects onto window
// via Jinja2 (window.donutSeries / window.donutLabels).
var currentSeries = window.donutSeries; 
var currentLabels = window.donutLabels; 

// ApexCharts Finance Donut Configuration
var options = {

    // ==========================================
    // 1. DATA LAYER
    // ==========================================

    // series holds the numeric values (e.g. [100, 150, 75, 200]).
    // ApexCharts sums them internally and sizes each donut segment
    // proportionally - e.g. 100 out of a 525 total renders as ~19%.
    series: currentSeries,

    // labels must stay index-aligned with series, so series[0]'s
    // segment is tagged with labels[0]'s name.
    labels: currentLabels,


    // ==========================================
    // 2. STRUCTURAL LAYER
    // ==========================================

    chart: {
        type: 'donut', // hollow center, as opposed to a solid pie
        height: 350    // pixels
    },


    // ==========================================
    // 3. INTERACTIVE LAYER (hover tooltip)
    // ==========================================

    tooltip: {
        y: {
            // Formats the hovered value as currency, e.g. 100 -> "£100.00".
            formatter: function (val) { 
                return "£" + val.toFixed(2); 
            }
        }
    },


    // ==========================================
    // 4. CORE GRAPHICS CONTROL
    // ==========================================

    // plotOptions holds chart-type-specific appearance settings -
    // here, everything nested under pie.donut only applies to the
    // hollow center area of this specific chart type.
    plotOptions: {
        pie: {
            donut: {
                labels: {
                    show: true, // false would leave the center blank

                    // The value shown in the center while hovering a segment.
                    value: {
                        show: true,
                        formatter: function (val) {
                            // Drops the decimal (100.00 -> 100) before
                            // prefixing the currency symbol.
                            return '£' + parseInt(val); 
                        }
                    },

                    // The default total shown in the center when no
                    // segment is being hovered.
                    total: {
                        show: true,
                        label: 'Total Revenue',

                        // w is the object ApexCharts passes in containing
                        // the chart's current global state and data.
                        //
                        // w.globals.seriesTotals holds the current series
                        // values, e.g. [100, 150, 75, 200]. reduce() walks
                        // that array left to right, adding each value into
                        // a running total starting from 0:
                        //   0 + 100 = 100 -> 100 + 150 = 250
                        //   250 + 75 = 325 -> 325 + 200 = 525
                        // The final total is then formatted as currency.
                        formatter: function (w) {
                            return '£' + w.globals.seriesTotals.reduce((a, b) => a + b, 0);
                        }
                    }
                }
            }
        }
    }
};

// ==========================================
// DOM-ready setup
// ==========================================
document.addEventListener('DOMContentLoaded', function () {
    
    // Only initializes the donut chart if its container exists on
    // this page - the same script.js is shared across pages that
    // don't all have a finance chart.
    var donutEl = document.querySelector("#finance-donut-chart");
    if (donutEl) {
        // Builds a new ApexCharts instance from the config above and
        // renders it into the donut container.
        var donutChart = new ApexCharts(donutEl, options);
        donutChart.render();
    }

    // Only initializes the calendar if its container exists on this
    // page, for the same reason as the donut chart above.
    var calendarE = document.querySelector('#calendar');
    if (calendarE){
        var calendar = new FullCalendar.Calendar(calendarE, {
            initialView: 'dayGridMonth',
            firstDay: 0,

            // Lesson events are fetched from the backend rather than
            // hardcoded, so the calendar always reflects the database.
            events: '/get_lessons',

            // Controls how each event renders on the calendar.
            eventContent: function(arg) {
                let startStr = arg.event.start.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true });
                let endStr = arg.event.end.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true });
                
                let customText = arg.event.title + ': ' + startStr + ' - ' + endStr;
                
                return { html: '<div class="fc-event-title">' + customText + '</div>' };
            },
                       
            // Shows lesson details in an alert when an event is clicked.
            eventClick: function(info) {
                var startTime = info.event.start.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                // Falls back to an empty string if the event has no end time.
                var endTime = info.event.end ? info.event.end.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';
                
                var message = info.event.title + ': ' + startTime + ' - ' + endTime;
                
                alert(message);
            }
        });
        
        calendar.render();
    }
});

document.addEventListener('DOMContentLoaded', () => {
    const lessonForm = document.getElementById('add-lesson-form');

    // Intercepts the lesson form submission to send it via AJAX
    // instead of a normal page-reloading POST.
    lessonForm.addEventListener('submit', async (e) => {
        e.preventDefault(); // stops the default full-page submit
        
        const formData = new FormData(lessonForm);

        const response = await fetch('/addlesson', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();

        if (data.success) {
            const lesson = data.lesson;

            // Calculate the next lesson number
            const lessonNumber =
                document.querySelectorAll('#lessonTableBody tr').length + 1;

            
            // Inserts the new lesson directly into both tables using
            // the server's JSON response, without reloading the page.
            document.getElementById('lessonTableBody').insertAdjacentHTML('beforeend', `
                <tr data-id="${lesson.id}">
                    <td>${lessonNumber}</td>
                    <td>${lesson.date}</td>
                    <td>${lesson.time}</td>
                    <td>${lesson.duration}</td>
                    <td>£${lesson.earnings}</td>
                    <td>${lesson.payment_status}</td>
                    <td>
                        <button
                            class="btn btn-danger btn-sm remove-lesson"
                            data-id="${lesson.id}">
                            Remove
                        </button>
                    </td>
                </tr>
            `);

            document.getElementById('progressTableBody').insertAdjacentHTML('beforeend', `
                <tr data-id="${lesson.id}"> 
                    <td>${lessonNumber}</td>
                    <td><input 
                    type="text" 
                    class="form-control form-control-sm spec-input" 
                    data-id="${lesson.id}" 
                    placeholder="Add progress..."></td>
                </tr>
            `);
            
            const modal = bootstrap.Modal.getInstance(document.getElementById('addLessonModal'));
            modal.hide();
            lessonForm.reset();
        }
    });

    // Auto-saves a progress note the moment its input loses focus,
    // so there's no separate save button to remember to click.
    document.addEventListener('blur', async (e) => {
        if (e.target.classList.contains('spec-input')) {
            const input = e.target;
            const response = await fetch('/update_spec', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: input.dataset.id, note: input.value })
            });
            const result = await response.json();
            if (result.success) {
                console.log("Notes auto-save is successful！");
            }
        }
    }, true);

document.addEventListener('click', async (e) => {

    if (!e.target.classList.contains('remove-lesson'))
        return;

    if (!confirm("Delete this lesson?"))
        return;

    const lessonId = e.target.dataset.id;

    const response = await fetch('/remove_lesson', {

        method: 'POST',

        headers: {
            'Content-Type': 'application/json'
        },

        body: JSON.stringify({
            id: lessonId
        })

    });

    const result = await response.json();

    if (result.success) {

         // Remove lesson row
        document
            .querySelector(`#lessonTableBody tr[data-id="${lessonId}"]`)
            ?.remove();

        // Remove progress row
        document
            .querySelector(`#progressTableBody tr[data-id="${lessonId}"]`)
            ?.remove();

        // Update lesson numbering
        renumberLessons();
    }

});    
});