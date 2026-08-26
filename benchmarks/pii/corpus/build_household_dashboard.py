import pandas as pd
import json
import os
import math

def build():
    csv_path = '/home/desinotorious/src/github.com/bprashanth/io/benchmarks/pii/corpus/household_survey.csv'
    cells_path = '/home/desinotorious/src/github.com/bprashanth/io/benchmarks/pii/corpus/household_survey.cells.json'
    
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return

    # Read CSV
    df = pd.read_csv(csv_path)

    # Read Ground Truth Spans for Redaction
    if os.path.exists(cells_path):
        with open(cells_path, 'r', encoding='utf-8') as f:
            cells_data = json.load(f)
    else:
        cells_data = []

    # Group spans by row index
    spans_by_row = {}
    for span in cells_data:
        r = span['row']
        if r not in spans_by_row:
            spans_by_row[r] = []
        spans_by_row[r].append(span)

    # Prepare records
    records = []
    total_redact_spans = 0
    
    for idx, row in df.iterrows():
        # Calculate duration
        try:
            start_dt = pd.to_datetime(row['start'])
            end_dt = pd.to_datetime(row['end'])
            duration = int(abs((end_dt - start_dt).total_seconds() / 60.0))
        except Exception:
            duration = 15 # fallback

        # Redact q26_remarks HTML
        remarks_raw = str(row['q26_remarks']) if pd.notna(row['q26_remarks']) else ""
        row_spans = spans_by_row.get(idx, [])
        total_redact_spans += len(row_spans)
        
        # Redaction replacement from right-to-left
        sorted_spans = sorted(row_spans, key=lambda x: x['start'], reverse=True)
        remarks_html = remarks_raw
        for span in sorted_spans:
            start = span['start']
            end = span['end']
            text = span['text']
            cls = span['class']
            placeholder = f'<span class="pii-span" data-class="{cls}" data-raw="{text}">{text}</span>'
            remarks_html = remarks_html[:start] + placeholder + remarks_html[end:]

        # Extract indicators
        indicators = {}
        for k in range(1, 26):
            col_name = f"q{str(k).zfill(2)}"
            val = row[col_name]
            if k % 3 == 1 or k == 25:
                # Numeric score
                indicators[col_name] = int(val) if pd.notna(val) else 0
            elif k % 3 == 2:
                # Rating
                indicators[col_name] = str(val) if pd.notna(val) else "Average"
            else:
                # Yes/No/Sometimes
                indicators[col_name] = str(val) if pd.notna(val) else "Sometimes"

        records.append({
            'id': int(row['_id']),
            'uuid': str(row['_uuid']),
            'start': str(row['start']),
            'end': str(row['end']),
            'duration': duration,
            'enumerator': str(row['enumerator_name']),
            'hh_head': str(row['hh_head_name']),
            'respondent': str(row['respondent_name']),
            'phone': str(row['respondent_phone']),
            'village': str(row['village']),
            'lat': float(row['gps_lat']) if pd.notna(row['gps_lat']) else 0.0,
            'lon': float(row['gps_lon']) if pd.notna(row['gps_lon']) else 0.0,
            'ration_card': str(row['ration_card_no']),
            'indicators': indicators,
            'remarks_raw': remarks_raw,
            'remarks_html': remarks_html,
            'has_pii': len(row_spans) > 0,
            'submission_time': str(row['_submission_time'])
        })

    json_data = json.dumps(records, indent=2)

    # HTML Template
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Survekshan: Household Survey Dashboard</title>
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <!-- FontAwesome for Icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <!-- Leaflet.js Map -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        :root {{
            --bg-primary: #0b0f19;
            --bg-secondary: #111827;
            --bg-tertiary: #1f2937;
            --bg-hover: #374151;
            --text-primary: #f9fafb;
            --text-secondary: #9ca3af;
            --border-color: #1f2937;
            --primary-color: #6366f1;
            --primary-hover: #4f46e5;
            --primary-glow: rgba(99, 102, 241, 0.15);
            --accent-color: #06b6d4;
            --success-color: #10b981;
            --success-glow: rgba(16, 185, 129, 0.15);
            --warning-color: #f59e0b;
            --warning-glow: rgba(245, 158, 11, 0.15);
            --danger-color: #ef4444;
            --danger-glow: rgba(239, 68, 68, 0.15);
            --card-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -2px rgba(0, 0, 0, 0.3);
            --font-display: 'Outfit', sans-serif;
            --font-body: 'Inter', sans-serif;
        }}

        body.light-theme {{
            --bg-primary: #f8fafc;
            --bg-secondary: #ffffff;
            --bg-tertiary: #f1f5f9;
            --bg-hover: #e2e8f0;
            --text-primary: #0f172a;
            --text-secondary: #64748b;
            --border-color: #cbd5e1;
            --primary-color: #4f46e5;
            --primary-hover: #4338ca;
            --primary-glow: rgba(79, 70, 229, 0.1);
            --accent-color: #0891b2;
            --success-color: #059669;
            --success-glow: rgba(5, 150, 105, 0.1);
            --warning-color: #d97706;
            --warning-glow: rgba(217, 119, 6, 0.1);
            --danger-color: #dc2626;
            --danger-glow: rgba(220, 38, 38, 0.1);
            --card-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: var(--font-body);
        }}

        body {{
            background-color: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            transition: background-color 0.3s, color 0.3s;
        }}

        /* Sidebar */
        aside {{
            width: 280px;
            background-color: var(--bg-secondary);
            border-right: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            padding: 24px;
            position: fixed;
            top: 0;
            bottom: 0;
            left: 0;
            z-index: 100;
            transition: background-color 0.3s, border-color 0.3s;
        }}

        .brand {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 24px;
        }}

        .brand-icon {{
            font-size: 1.8rem;
            color: var(--primary-color);
        }}

        .brand-name h1 {{
            font-family: var(--font-display);
            font-size: 1.3rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--primary-color), var(--accent-color));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .brand-name p {{
            font-size: 0.75rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        /* PII Security Shield Widget */
        .pii-shield-widget {{
            background-color: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 24px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}

        .pii-widget-header {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.85rem;
            font-weight: 600;
        }}

        .pii-widget-header i {{
            color: var(--success-color);
            font-size: 1rem;
        }}
        
        .pii-widget-header.unsecure i {{
            color: var(--danger-color);
        }}

        /* Switch toggle styling */
        .switch-container {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: rgba(0, 0, 0, 0.2);
            padding: 8px 12px;
            border-radius: 8px;
            border: 1px solid var(--border-color);
        }}

        .switch-label {{
            font-size: 0.8rem;
            font-weight: 500;
            color: var(--text-secondary);
        }}

        .switch {{
            position: relative;
            display: inline-block;
            width: 44px;
            height: 22px;
        }}

        .switch input {{
            opacity: 0;
            width: 0;
            height: 0;
        }}

        .slider {{
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: var(--bg-hover);
            transition: .4s;
            border-radius: 22px;
        }}

        .slider:before {{
            position: absolute;
            content: "";
            height: 16px;
            width: 16px;
            left: 3px;
            bottom: 3px;
            background-color: white;
            transition: .4s;
            border-radius: 50%;
        }}

        input:checked + .slider {{
            background-color: var(--success-color);
        }}
        
        input:focus + .slider {{
            box-shadow: 0 0 1px var(--success-color);
        }}

        input:checked + .slider:before {{
            transform: translateX(22px);
        }}

        .nav-links {{
            display: flex;
            flex-direction: column;
            gap: 6px;
            list-style: none;
            flex: 1;
        }}

        .nav-item {{
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 10px 14px;
            border-radius: 8px;
            color: var(--text-secondary);
            text-decoration: none;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
        }}

        .nav-item:hover, .nav-item.active {{
            color: var(--text-primary);
            background-color: var(--primary-glow);
        }}

        .nav-item.active {{
            border-left: 4px solid var(--primary-color);
            border-radius: 0 8px 8px 0;
            padding-left: 10px;
            background-color: var(--primary-glow);
            color: var(--primary-color);
        }}

        .nav-item i {{
            font-size: 1.1rem;
            width: 24px;
            text-align: center;
        }}

        .sidebar-footer {{
            margin-top: auto;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}

        .theme-toggle-btn {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 10px;
            border-radius: 8px;
            background-color: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            cursor: pointer;
            font-weight: 600;
            font-size: 0.85rem;
            transition: all 0.2s;
        }}

        .theme-toggle-btn:hover {{
            background-color: var(--bg-hover);
        }}

        /* Main Area */
        main {{
            flex: 1;
            margin-left: 280px;
            padding: 40px;
            max-width: 1500px;
            width: calc(100% - 280px);
        }}

        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 28px;
        }}

        .page-title h2 {{
            font-family: var(--font-display);
            font-size: 1.8rem;
            font-weight: 700;
        }}

        .page-title p {{
            color: var(--text-secondary);
            font-size: 0.9rem;
            margin-top: 4px;
        }}

        /* KPIs */
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 18px;
            margin-bottom: 28px;
        }}

        .kpi-card {{
            background-color: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            box-shadow: var(--card-shadow);
            position: relative;
            overflow: hidden;
            transition: transform 0.2s, border-color 0.2s;
        }}

        .kpi-card:hover {{
            transform: translateY(-2px);
            border-color: var(--primary-color);
        }}

        .kpi-card::after {{
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            width: 100%;
            height: 4px;
            background-color: var(--accent);
        }}

        .kpi-card.surveys::after {{ --accent: var(--primary-color); }}
        .kpi-card.villages::after {{ --accent: var(--success-color); }}
        .kpi-card.enumerators::after {{ --accent: var(--warning-color); }}
        .kpi-card.duration::after {{ --accent: var(--accent-color); }}
        .kpi-card.pii-redacted::after {{ --accent: var(--danger-color); }}

        .kpi-info h3 {{
            font-size: 0.8rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 6px;
        }}

        .kpi-value {{
            font-family: var(--font-display);
            font-size: 1.68rem;
            font-weight: 700;
            line-height: 1.2;
        }}

        .kpi-subtext {{
            font-size: 0.75rem;
            color: var(--text-secondary);
            margin-top: 4px;
        }}

        .kpi-icon {{
            width: 40px;
            height: 40px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
        }}

        .surveys .kpi-icon {{ background-color: var(--primary-glow); color: var(--primary-color); }}
        .villages .kpi-icon {{ background-color: var(--success-glow); color: var(--success-color); }}
        .enumerators .kpi-icon {{ background-color: var(--warning-glow); color: var(--warning-color); }}
        .duration .kpi-icon {{ background-color: rgba(6, 182, 212, 0.15); color: var(--accent-color); }}
        .pii-redacted .kpi-icon {{ background-color: var(--danger-glow); color: var(--danger-color); }}

        /* Charts */
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 24px;
            margin-bottom: 28px;
        }}

        @media (max-width: 1024px) {{
            .charts-grid {{
                grid-template-columns: 1fr;
            }}
        }}

        .chart-card {{
            background-color: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
            box-shadow: var(--card-shadow);
            display: flex;
            flex-direction: column;
            min-height: 340px;
        }}

        .chart-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }}

        .chart-title {{
            font-family: var(--font-display);
            font-size: 1rem;
            font-weight: 600;
        }}

        .chart-title i {{
            margin-right: 6px;
            color: var(--primary-color);
        }}

        .chart-container {{
            position: relative;
            flex: 1;
            width: 100%;
            height: 100%;
        }}

        /* Sections Toggle */
        section {{
            display: none;
        }}

        section.active-section {{
            display: block;
            animation: fadeIn 0.4s ease;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        /* Map styling */
        #map-container {{
            width: 100%;
            height: 550px;
            border-radius: 12px;
            border: 1px solid var(--border-color);
            box-shadow: var(--card-shadow);
        }}

        /* Table */
        .data-section {{
            background-color: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            box-shadow: var(--card-shadow);
            overflow: hidden;
            margin-bottom: 28px;
        }}

        .filters-panel {{
            padding: 20px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            gap: 14px;
            background-color: rgba(0, 0, 0, 0.1);
        }}

        body.light-theme .filters-panel {{
            background-color: rgba(0, 0, 0, 0.02);
        }}

        .search-row {{
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
        }}

        .search-box-container {{
            position: relative;
            flex: 1;
            min-width: 250px;
        }}

        .search-box-container i {{
            position: absolute;
            left: 14px;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-secondary);
        }}

        .search-input {{
            width: 100%;
            padding: 10px 14px 10px 42px;
            border-radius: 8px;
            background-color: var(--bg-primary);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            outline: none;
            font-size: 0.9rem;
            transition: all 0.2s;
        }}

        .search-input:focus {{
            border-color: var(--primary-color);
            box-shadow: 0 0 0 2px var(--primary-glow);
        }}

        .filter-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            align-items: center;
        }}

        .filter-select {{
            padding: 8px 12px;
            border-radius: 8px;
            background-color: var(--bg-primary);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            outline: none;
            font-size: 0.8rem;
            min-width: 140px;
            cursor: pointer;
            transition: all 0.2s;
        }}

        .clear-filters-btn {{
            padding: 8px 14px;
            border-radius: 8px;
            background-color: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            cursor: pointer;
            font-weight: 500;
            font-size: 0.8rem;
            transition: all 0.2s;
        }}

        .clear-filters-btn:hover {{
            background-color: var(--bg-hover);
        }}

        .table-responsive {{
            overflow-x: auto;
            width: 100%;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }}

        th {{
            background-color: rgba(0, 0, 0, 0.2);
            padding: 14px 18px;
            color: var(--text-secondary);
            font-weight: 600;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 1px solid var(--border-color);
            cursor: pointer;
            user-select: none;
            transition: background-color 0.2s;
        }}

        body.light-theme th {{
            background-color: rgba(0, 0, 0, 0.04);
        }}

        th:hover {{
            background-color: rgba(0, 0, 0, 0.3);
        }}

        td {{
            padding: 12px 18px;
            border-bottom: 1px solid var(--border-color);
            font-size: 0.85rem;
            vertical-align: middle;
        }}

        tr:last-child td {{
            border-bottom: none;
        }}

        tr:hover td {{
            background-color: rgba(255, 255, 255, 0.02);
        }}

        body.light-theme tr:hover td {{
            background-color: rgba(0, 0, 0, 0.01);
        }}

        /* PII Spans Highlights */
        .pii-span {{
            padding: 2px 6px;
            border-radius: 4px;
            font-family: inherit;
            font-size: inherit;
            font-weight: 500;
            transition: all 0.3s;
        }}

        .pii-span.secure {{
            background-color: var(--danger-glow);
            color: var(--danger-color);
            border: 1px dashed var(--danger-color);
            cursor: not-allowed;
            font-size: 0.75rem;
        }}

        .pii-span.raw {{
            background-color: var(--warning-glow);
            color: var(--warning-color);
            border: 1px solid var(--warning-color);
            cursor: help;
        }}

        /* Badges */
        .badge {{
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 3px 8px;
            border-radius: 9999px;
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
        }}

        .badge-good {{ background-color: var(--success-glow); color: var(--success-color); }}
        .badge-average {{ background-color: var(--warning-glow); color: var(--warning-color); }}
        .badge-poor {{ background-color: var(--danger-glow); color: var(--danger-color); }}

        .badge-yes {{ background-color: var(--success-glow); color: var(--success-color); }}
        .badge-sometimes {{ background-color: var(--warning-glow); color: var(--warning-color); }}
        .badge-no {{ background-color: var(--danger-glow); color: var(--danger-color); }}

        .btn-view {{
            background-color: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            padding: 5px 10px;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }}

        .btn-view:hover {{
            background-color: var(--bg-hover);
            border-color: var(--primary-color);
        }}

        /* Pagination */
        .pagination-bar {{
            padding: 14px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-top: 1px solid var(--border-color);
            background-color: rgba(0, 0, 0, 0.1);
        }}

        body.light-theme .pagination-bar {{
            background-color: rgba(0, 0, 0, 0.02);
        }}

        .pagination-info {{
            font-size: 0.8rem;
            color: var(--text-secondary);
        }}

        .pagination-controls {{
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .page-btn {{
            padding: 6px 10px;
            border-radius: 6px;
            border: 1px solid var(--border-color);
            background-color: var(--bg-primary);
            color: var(--text-primary);
            font-size: 0.8rem;
            cursor: pointer;
            transition: all 0.2s;
        }}

        .page-btn:hover:not(:disabled) {{
            background-color: var(--primary-color);
            color: white;
            border-color: var(--primary-color);
        }}

        .page-btn:disabled {{
            opacity: 0.4;
            cursor: not-allowed;
        }}

        /* Modals */
        .modal-overlay {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: rgba(0, 0, 0, 0.7);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 1000;
            animation: fadeIn 0.2s ease;
        }}

        .modal-container {{
            background-color: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            width: 90%;
            max-width: 950px;
            max-height: 85vh;
            overflow-y: auto;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.4);
            animation: slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }}

        @keyframes slideUp {{
            from {{ transform: translateY(30px); opacity: 0; }}
            to {{ transform: translateY(0); opacity: 1; }}
        }}

        .modal-header {{
            padding: 20px 24px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .modal-title h3 {{
            font-family: var(--font-display);
            font-size: 1.25rem;
            font-weight: 700;
        }}

        .modal-close-btn {{
            background: none;
            border: none;
            font-size: 1.4rem;
            color: var(--text-secondary);
            cursor: pointer;
            transition: color 0.2s;
        }}

        .modal-close-btn:hover {{
            color: var(--text-primary);
        }}

        .modal-body {{
            padding: 24px;
        }}

        /* Detail grids */
        .detail-sections-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }}

        @media (max-width: 768px) {{
            .detail-sections-grid {{
                grid-template-columns: 1fr;
            }}
        }}

        .detail-card {{
            background-color: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 16px;
        }}

        .detail-card-title {{
            font-family: var(--font-display);
            font-size: 0.9rem;
            font-weight: 600;
            margin-bottom: 12px;
            color: var(--primary-color);
            display: flex;
            align-items: center;
            gap: 8px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 6px;
        }}

        .detail-row {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            font-size: 0.85rem;
        }}

        .detail-row:last-child {{
            margin-bottom: 0;
        }}

        .detail-label {{
            color: var(--text-secondary);
        }}

        .detail-val {{
            font-weight: 500;
        }}

        .details-indicators-list {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 12px;
        }}

        .indicator-item {{
            background-color: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .indicator-item-info h5 {{
            font-size: 0.8rem;
            font-weight: 600;
            margin-bottom: 2px;
        }}

        .indicator-item-info p {{
            font-size: 0.7rem;
            color: var(--text-secondary);
        }}

        /* Enumerators view grid */
        .enumerators-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 20px;
            margin-bottom: 28px;
        }}

        .enum-card {{
            background-color: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
            box-shadow: var(--card-shadow);
        }}

        .enum-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 16px;
        }}

        .enum-avatar {{
            width: 48px;
            height: 48px;
            border-radius: 50%;
            background-color: var(--primary-glow);
            color: var(--primary-color);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.4rem;
            font-weight: 700;
            font-family: var(--font-display);
        }}

        .enum-meta h4 {{
            font-family: var(--font-display);
            font-weight: 600;
            font-size: 0.95rem;
        }}

        .enum-meta p {{
            font-size: 0.75rem;
            color: var(--text-secondary);
        }}

        .enum-stats-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            background-color: var(--bg-tertiary);
            padding: 10px;
            border-radius: 8px;
            text-align: center;
            margin-bottom: 12px;
        }}

        .enum-stat-val {{
            font-size: 1.15rem;
            font-weight: 700;
            font-family: var(--font-display);
        }}

        .enum-stat-lbl {{
            font-size: 0.65rem;
            color: var(--text-secondary);
            text-transform: uppercase;
        }}

        /* Village Select */
        .village-profile-header {{
            background-color: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 28px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
        }}

        .village-selector-wrapper {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .village-selector-wrapper label {{
            font-size: 0.9rem;
            font-weight: 600;
            color: var(--text-secondary);
        }}

        .village-dropdown {{
            padding: 10px 16px;
            border-radius: 8px;
            background-color: var(--bg-primary);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            outline: none;
            font-size: 0.95rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }}

        .village-dropdown:focus {{
            border-color: var(--primary-color);
        }}
    </style>
</head>
<body>
    <!-- Sidebar -->
    <aside>
        <div class="brand">
            <i class="fa-solid fa-house-laptop brand-icon"></i>
            <div class="brand-name">
                <h1>Survekshan</h1>
                <p>Household Insights</p>
            </div>
        </div>

        <!-- PII Shield Widget -->
        <div class="pii-shield-widget" id="pii-widget">
            <div class="pii-widget-header" id="pii-header">
                <i class="fa-solid fa-shield-halved"></i>
                <span>PII PROTECTION ACTIVE</span>
            </div>
            <div class="switch-container">
                <span class="switch-label">Secure Mode</span>
                <label class="switch">
                    <input type="checkbox" id="pii-secure-toggle" checked>
                    <span class="slider"></span>
                </label>
            </div>
            <div style="font-size: 0.7rem; color: var(--text-secondary); line-height: 1.4;">
                Hides personal identifiers (names, phones, ration cards, exact GPS) and redacts text remarks.
            </div>
        </div>

        <!-- Nav links -->
        <ul class="nav-links">
            <li>
                <a class="nav-item active" onclick="switchSection('dashboard', this)">
                    <i class="fa-solid fa-chart-line"></i>
                    <span>Dashboard</span>
                </a>
            </li>
            <li>
                <a class="nav-item" onclick="switchSection('map', this)">
                    <i class="fa-solid fa-map-location-dot"></i>
                    <span>Geographic Map</span>
                </a>
            </li>
            <li>
                <a class="nav-item" onclick="switchSection('enumerators', this)">
                    <i class="fa-solid fa-user-tie"></i>
                    <span>Enumerators</span>
                </a>
            </li>
            <li>
                <a class="nav-item" onclick="switchSection('villages', this)">
                    <i class="fa-solid fa-building-user"></i>
                    <span>Village Profiles</span>
                </a>
            </li>
            <li>
                <a class="nav-item" onclick="switchSection('raw-data', this)">
                    <i class="fa-solid fa-database"></i>
                    <span>Raw Survey Data</span>
                </a>
            </li>
        </ul>

        <div class="sidebar-footer">
            <button class="theme-toggle-btn" onclick="toggleTheme()">
                <i class="fa-solid fa-moon"></i>
                <span id="theme-btn-text">Toggle Theme</span>
            </button>
            <div style="font-size: 0.75rem; text-align: center; color: var(--text-secondary);">
                v1.1.0 • Built with Antigravity
            </div>
        </div>
    </aside>

    <!-- Main Workspace -->
    <main>
        <!-- Section: Dashboard -->
        <section id="section-dashboard" class="active-section">
            <header>
                <div class="page-title">
                    <h2>Survey Analytics Overview</h2>
                    <p>Aggregated metrics and statistical insights from the local household survey dataset</p>
                </div>
            </header>

            <!-- KPIs -->
            <div class="kpi-grid">
                <div class="kpi-card surveys">
                    <div class="kpi-info">
                        <h3>Total Surveyed</h3>
                        <div class="kpi-value" id="kpi-total-surveys">150</div>
                        <div class="kpi-subtext">Completed sessions</div>
                    </div>
                    <div class="kpi-icon">
                        <i class="fa-solid fa-clipboard-question"></i>
                    </div>
                </div>
                <div class="kpi-card villages">
                    <div class="kpi-info">
                        <h3>Villages Covered</h3>
                        <div class="kpi-value" id="kpi-total-villages">0</div>
                        <div class="kpi-subtext">Across Muzaffarpur, Gaya, Pune</div>
                    </div>
                    <div class="kpi-icon">
                        <i class="fa-solid fa-map-pin"></i>
                    </div>
                </div>
                <div class="kpi-card enumerators">
                    <div class="kpi-info">
                        <h3>Active Surveyors</h3>
                        <div class="kpi-value" id="kpi-total-enumerators">0</div>
                        <div class="kpi-subtext">Field agents deployed</div>
                    </div>
                    <div class="kpi-icon">
                        <i class="fa-solid fa-users"></i>
                    </div>
                </div>
                <div class="kpi-card duration">
                    <div class="kpi-info">
                        <h3>Avg Survey Duration</h3>
                        <div class="kpi-value" id="kpi-avg-duration">0m</div>
                        <div class="kpi-subtext">Time per interview</div>
                    </div>
                    <div class="kpi-icon">
                        <i class="fa-solid fa-hourglass-half"></i>
                    </div>
                </div>
                <div class="kpi-card pii-redacted">
                    <div class="kpi-info">
                        <h3>Redactions Ground Truth</h3>
                        <div class="kpi-value" id="kpi-total-redactions">{total_redact_spans}</div>
                        <div class="kpi-subtext">PII Spans detected</div>
                    </div>
                    <div class="kpi-icon">
                        <i class="fa-solid fa-user-shield"></i>
                    </div>
                </div>
            </div>

            <!-- Charts Grid -->
            <div class="charts-grid">
                <div class="chart-card">
                    <div class="chart-header">
                        <div class="chart-title"><i class="fa-solid fa-circle-dot"></i>Average Performance Indicator Profiles</div>
                    </div>
                    <div class="chart-container">
                        <canvas id="chart-indicators"></canvas>
                    </div>
                </div>
                <div class="chart-card">
                    <div class="chart-header">
                        <div class="chart-title"><i class="fa-solid fa-chart-column"></i>Survey Category Rating Distributions</div>
                    </div>
                    <div class="chart-container">
                        <canvas id="chart-ratings"></canvas>
                    </div>
                </div>
                <div class="chart-card">
                    <div class="chart-header">
                        <div class="chart-title"><i class="fa-solid fa-pie-chart"></i>Surveys Completed by Village</div>
                    </div>
                    <div class="chart-container">
                        <canvas id="chart-villages"></canvas>
                    </div>
                </div>
                <div class="chart-card">
                    <div class="chart-header">
                        <div class="chart-title"><i class="fa-solid fa-calendar-alt"></i>Survey Submission Trend</div>
                    </div>
                    <div class="chart-container">
                        <canvas id="chart-trends"></canvas>
                    </div>
                </div>
            </div>
        </section>

        <!-- Section: Map -->
        <section id="section-map">
            <header>
                <div class="page-title">
                    <h2>Geographic Distribution Map</h2>
                    <p>Spatial plot of the surveyed households. GPS positions are coarsened in Secure Mode to protect privacy.</p>
                </div>
            </header>
            <div id="map-container"></div>
        </section>

        <!-- Section: Enumerators -->
        <section id="section-enumerators">
            <header>
                <div class="page-title">
                    <h2>Field Surveyor Performance</h2>
                    <p>Breakdown of surveys completed, average interview times, and PII compliance metrics by enumerator</p>
                </div>
            </header>
            <div class="enumerators-grid" id="enum-cards-container"></div>
        </section>

        <!-- Section: Villages -->
        <section id="section-villages">
            <div class="village-profile-header">
                <div class="page-title">
                    <h2>Village-Level Detailed Analysis</h2>
                    <p>Detailed indicator averages and metrics filters by target village</p>
                </div>
                <div class="village-selector-wrapper">
                    <label for="village-profile-select">Selected Village:</label>
                    <select class="village-dropdown" id="village-profile-select" onchange="loadVillageProfile(this.value)">
                        <!-- Loaded dynamically -->
                    </select>
                </div>
            </div>

            <!-- KPIs specific to village -->
            <div class="kpi-grid" id="village-kpi-grid">
                <!-- Loaded dynamically -->
            </div>

            <div class="charts-grid">
                <div class="chart-card" style="grid-column: span 2;">
                    <div class="chart-header">
                        <div class="chart-title"><i class="fa-solid fa-chart-line"></i>Village Survey Response Profile</div>
                    </div>
                    <div class="chart-container" style="min-height: 380px;">
                        <canvas id="chart-village-radar"></canvas>
                    </div>
                </div>
            </div>
        </section>

        <!-- Section: Raw Data Table -->
        <section id="section-raw-data">
            <header>
                <div class="page-title">
                    <h2>Raw Survey Ledger</h2>
                    <p>Browse, filter, and export the complete household survey dataset. Switch Secure Mode to toggle PII visibility.</p>
                </div>
            </header>

            <div class="data-section">
                <!-- Filters -->
                <div class="filters-panel">
                    <div class="search-row">
                        <div class="search-box-container">
                            <i class="fa-solid fa-magnifying-glass"></i>
                            <input type="text" class="search-input" id="table-search" placeholder="Search by names, ID, phone, village..." oninput="handleFilterChange()">
                        </div>
                    </div>
                    <div class="filter-row">
                        <select class="filter-select" id="filter-village" onchange="handleFilterChange()">
                            <option value="">All Villages</option>
                        </select>
                        <select class="filter-select" id="filter-enumerator" onchange="handleFilterChange()">
                            <option value="">All Enumerators</option>
                        </select>
                        <select class="filter-select" id="filter-pii" onchange="handleFilterChange()">
                            <option value="">All Remarks</option>
                            <option value="has_pii">Has Remarks PII</option>
                            <option value="no_pii">No Remarks PII</option>
                        </select>
                        <button class="clear-filters-btn" onclick="clearFilters()">
                            <i class="fa-solid fa-filter-circle-xmark"></i> Clear Filters
                        </button>
                        
                        <button class="clear-filters-btn" onclick="exportCSV()" style="margin-left: auto; background-color: var(--primary-color); color: white; border: none;">
                            <i class="fa-solid fa-file-csv"></i> Export CSV
                        </button>
                    </div>
                </div>

                <!-- Table -->
                <div class="table-responsive">
                    <table id="survey-table">
                        <thead>
                            <tr>
                                <th onclick="handleSort('id')">ID</th>
                                <th onclick="handleSort('hh_head')">HH Head</th>
                                <th onclick="handleSort('respondent')">Respondent</th>
                                <th onclick="handleSort('village')">Village</th>
                                <th onclick="handleSort('enumerator')">Enumerator</th>
                                <th onclick="handleSort('duration')">Duration</th>
                                <th>Remarks / Notes</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="survey-table-body">
                            <!-- Loaded dynamically -->
                        </tbody>
                    </table>
                </div>

                <!-- Pagination -->
                <div class="pagination-bar">
                    <div class="pagination-info" id="pagination-info">
                        Showing 1 to 10 of 150 entries
                    </div>
                    <div class="pagination-controls">
                        <button class="page-btn" id="btn-prev-page" onclick="prevPage()"><i class="fa-solid fa-chevron-left"></i> Previous</button>
                        <button class="page-btn" id="btn-next-page" onclick="nextPage()">Next <i class="fa-solid fa-chevron-right"></i></button>
                    </div>
                </div>
            </div>
        </section>
    </main>

    <!-- Modal for Survey Detail -->
    <div class="modal-overlay" id="detail-modal" onclick="closeModal(event)">
        <div class="modal-container" onclick="event.stopPropagation()">
            <div class="modal-header">
                <div class="modal-title">
                    <h3 id="modal-title-text">Household Survey Detail</h3>
                    <p style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 4px;" id="modal-subtitle-text">ID: 90001 • UUID: 000-000</p>
                </div>
                <button class="modal-close-btn" onclick="closeModal()"><i class="fa-solid fa-xmark"></i></button>
            </div>
            <div class="modal-body">
                <div class="detail-sections-grid">
                    <!-- Household Meta -->
                    <div class="detail-card">
                        <div class="detail-card-title">
                            <i class="fa-solid fa-id-card"></i> Personal Identifiers (PII)
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">HH Head Name</span>
                            <span class="detail-val" id="detail-head">John Doe</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Respondent Name</span>
                            <span class="detail-val" id="detail-respondent">Jane Doe</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Contact Number</span>
                            <span class="detail-val" id="detail-phone">9999999999</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Ration Card No</span>
                            <span class="detail-val" id="detail-ration">MH12345</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">GPS Coordinates</span>
                            <span class="detail-val" id="detail-gps">0.0, 0.0</span>
                        </div>
                    </div>

                    <!-- Survey Info -->
                    <div class="detail-card">
                        <div class="detail-card-title">
                            <i class="fa-solid fa-circle-info"></i> Survey Metadata
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Village</span>
                            <span class="detail-val" id="detail-village">Village</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Enumerator</span>
                            <span class="detail-val" id="detail-enumerator">Enumerator</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Survey Start</span>
                            <span class="detail-val" id="detail-start">Start</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Survey End</span>
                            <span class="detail-val" id="detail-end">End</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Interview Duration</span>
                            <span class="detail-val" id="detail-duration">15 mins</span>
                        </div>
                    </div>
                </div>

                <!-- Remarks -->
                <div class="detail-card" style="margin-bottom: 20px;">
                    <div class="detail-card-title">
                        <i class="fa-solid fa-quote-left"></i> Field Notes & Remarks
                    </div>
                    <div id="detail-remarks-body" style="font-size: 0.9rem; line-height: 1.6; padding: 12px; background: rgba(0,0,0,0.1); border-radius: 8px;">
                        Remarks text here.
                    </div>
                </div>

                <!-- Indicators -->
                <div class="detail-card">
                    <div class="detail-card-title">
                        <i class="fa-solid fa-sliders"></i> Performance Indicators (q01 - q25)
                    </div>
                    <div class="details-indicators-list" id="detail-indicators-list">
                        <!-- Loaded dynamically -->
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Embedded Data & Script -->
    <script>
        // Survey Questions config
        const questionLabels = {{
            "q01": {{ label: "Housing Quality Score", type: "score", category: "Housing", desc: "Overall structural score of the housing unit (0-10)" }},
            "q02": {{ label: "Housing Condition Rating", type: "rating", category: "Housing", desc: "General rating of the house state" }},
            "q03": {{ label: "Pucca Roof Presence", type: "frequency", category: "Housing", desc: "Is the roof constructed of permanent (pucca) materials?" }},
            "q04": {{ label: "Toilet Quality Score", type: "score", category: "Sanitation", desc: "Overall score of the toilet facility (0-10)" }},
            "q05": {{ label: "Sanitation Quality Rating", type: "rating", category: "Sanitation", desc: "General hygiene and facility rating" }},
            "q06": {{ label: "Handwashing Station Access", type: "frequency", category: "Sanitation", desc: "Is there a handwashing facility near the toilet?" }},
            "q07": {{ label: "Water Access Score", type: "score", category: "Water & Health", desc: "Score for clean drinking water access (0-10)" }},
            "q08": {{ label: "Water Quality Rating", type: "rating", category: "Water & Health", desc: "General rating of water purity/taste" }},
            "q09": {{ label: "Water Supply Reliability", type: "frequency", category: "Water & Health", desc: "Daily availability of drinking water" }},
            "q10": {{ label: "Health Center Proximity Score", type: "score", category: "Water & Health", desc: "Access and proximity score to medical services (0-10)" }},
            "q11": {{ label: "Health Center Service Rating", type: "rating", category: "Water & Health", desc: "Quality rating of nearest health center services" }},
            "q12": {{ label: "Recent Illness Indicator", type: "frequency", category: "Water & Health", desc: "Did any family member fall ill in the last month?" }},
            "q13": {{ label: "Income Stability Score", type: "score", category: "Livelihood", desc: "Score of monthly household earnings consistency (0-10)" }},
            "q14": {{ label: "Livelihood Security Rating", type: "rating", category: "Livelihood", desc: "Overall rating of job security and income adequacy" }},
            "q15": {{ label: "MNREGA Work Access", type: "frequency", category: "Livelihood", desc: "Does the household get regular public works employment?" }},
            "q16": {{ label: "Financial Savings Score", type: "score", category: "Livelihood", desc: "Score of family cash reserves and savings behavior (0-10)" }},
            "q17": {{ label: "Savings Account Rating", type: "rating", category: "Livelihood", desc: "Rating of formal bank account usage and access" }},
            "q18": {{ label: "Debt Burden Presence", type: "frequency", category: "Livelihood", desc: "Does the household have active high-interest debts?" }},
            "q19": {{ label: "School Enrollment Score", type: "score", category: "Education", desc: "Enrollment rate of school-age children (0-10)" }},
            "q20": {{ label: "School Infrastructure Rating", type: "rating", category: "Education", desc: "Quality rating of the local school facilities" }},
            "q21": {{ label: "Out of School Children", type: "frequency", category: "Education", desc: "Are there any school-age children out of school?" }},
            "q22": {{ label: "Social Inclusion Score", type: "score", category: "Education", desc: "Score of social inclusion and community participation (0-10)" }},
            "q23": {{ label: "Community Safety Rating", type: "rating", category: "Education", desc: "Rating of safety and peace in the neighborhood" }},
            "q24": {{ label: "Welfare Scheme Access", type: "frequency", category: "Education", desc: "Does the household receive social welfare benefits?" }},
            "q25": {{ label: "Development Index Score", type: "score", category: "Overall", desc: "Composite household development and wellness score (0-10)" }}
        }};

        // Data source
        const dataset = {json_data};

        // State variables
        let isSecureMode = true;
        let activeSection = 'dashboard';
        let currentTheme = 'dark';
        
        // Table filtering and pagination state
        let filteredData = [...dataset];
        let currentPage = 1;
        const rowsPerPage = 10;
        let sortColumn = 'id';
        let sortDirection = 'asc';

        // Map state
        let leafMap = null;
        let markerLayer = null;

        // Chart instances
        let chartIndicators = null;
        let chartRatings = null;
        let chartVillages = null;
        let chartTrends = null;
        let chartVillageRadar = null;

        // Masking helpers
        function maskName(name) {{
            if (!name) return "";
            return name.split(" ").map(word => {{
                if (word.length <= 1) return word;
                return word[0] + "*".repeat(word.length - 1);
            }}).join(" ");
        }}

        function maskPhone(phone) {{
            if (!phone) return "";
            if (phone.length <= 6) return "***-***";
            return phone.substring(0, 4) + "****" + phone.substring(phone.length - 3);
        }}

        function maskRationCard(card) {{
            if (!card) return "";
            if (card.length <= 4) return "****";
            return card.substring(0, 4) + "*".repeat(card.length - 6) + card.substring(card.length - 2);
        }}

        function maskGPS(lat, lon, isSecure) {{
            if (isSecure) {{
                return `${{Math.round(lat * 100) / 100}}° N, ${{Math.round(lon * 100) / 100}}° E (Coarsened)`;
            }}
            return `${{lat.toFixed(4)}}° N, ${{lon.toFixed(4)}}° E`;
        }}

        function formatRemarks(remarksHtml, isSecure) {{
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = remarksHtml;
            const piiSpans = tempDiv.querySelectorAll('.pii-span');
            piiSpans.forEach(span => {{
                const cls = span.getAttribute('data-class');
                const raw = span.getAttribute('data-raw');
                if (isSecure) {{
                    span.className = 'pii-span secure';
                    span.textContent = `[REDACTED: ${{cls.replace('_', ' ')}}]`;
                    span.title = 'Personal identifier hidden for protection';
                }} else {{
                    span.className = 'pii-span raw';
                    span.textContent = raw;
                    span.title = `PII detected: ${{cls.replace('_', ' ')}}`;
                }}
            }});
            return tempDiv.innerHTML;
        }}

        // Initialize dashboard
        window.addEventListener('DOMContentLoaded', () => {{
            initDashboardMetrics();
            initCharts();
            populateFilterOptions();
            renderTable();
            initPiiToggle();
            
            // Initial village dropdown for profile tab
            const villageSelect = document.getElementById('village-profile-select');
            const villages = [...new Set(dataset.map(r => r.village))].sort();
            villages.forEach(v => {{
                const opt = document.createElement('option');
                opt.value = v;
                opt.textContent = v;
                villageSelect.appendChild(opt);
            }});
            if (villages.length > 0) {{
                loadVillageProfile(villages[0]);
            }}
        }});

        function initDashboardMetrics() {{
            const totalSurveys = dataset.length;
            const villages = new Set(dataset.map(r => r.village)).size;
            const enumerators = new Set(dataset.map(r => r.enumerator)).size;
            const avgDuration = Math.round(dataset.reduce((sum, r) => sum + r.duration, 0) / totalSurveys);

            document.getElementById('kpi-total-surveys').textContent = totalSurveys;
            document.getElementById('kpi-total-villages').textContent = villages;
            document.getElementById('kpi-total-enumerators').textContent = enumerators;
            document.getElementById('kpi-avg-duration').textContent = `${{avgDuration}}m`;
        }}

        function initPiiToggle() {{
            const toggle = document.getElementById('pii-secure-toggle');
            const widget = document.getElementById('pii-widget');
            const header = document.getElementById('pii-header');
            
            toggle.addEventListener('change', (e) => {{
                isSecureMode = e.target.checked;
                if (isSecureMode) {{
                    header.className = 'pii-widget-header';
                    header.innerHTML = '<i class="fa-solid fa-shield-halved"></i> <span>PII PROTECTION ACTIVE</span>';
                }} else {{
                    header.className = 'pii-widget-header unsecure';
                    header.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> <span>PII PROTECTION DISABLED</span>';
                }}
                
                // Rerender table, maps and detail view
                renderTable();
                updateMapMarkers();
                renderEnumeratorCards();
            }});
        }}

        // Tab Switching
        function switchSection(sectId, navEl) {{
            activeSection = sectId;
            document.querySelectorAll('section').forEach(s => s.classList.remove('active-section'));
            document.getElementById(`section-${{sectId}}`).classList.add('active-section');

            document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
            navEl.classList.add('active');

            if (sectId === 'map') {{
                setTimeout(() => {{
                    if (!leafMap) {{
                        initMap();
                    }}
                    updateMapMarkers();
                }}, 100);
            }} else if (sectId === 'enumerators') {{
                renderEnumeratorCards();
            }}
        }}

        // Theme Toggle
        function toggleTheme() {{
            const body = document.body;
            const themeBtnIcon = document.querySelector('.theme-toggle-btn i');
            const themeBtnText = document.getElementById('theme-btn-text');

            if (currentTheme === 'dark') {{
                body.classList.add('light-theme');
                currentTheme = 'light';
                themeBtnIcon.className = 'fa-solid fa-sun';
                themeBtnText.textContent = 'Light Mode';
            }} else {{
                body.classList.remove('light-theme');
                currentTheme = 'dark';
                themeBtnIcon.className = 'fa-solid fa-moon';
                themeBtnText.textContent = 'Dark Mode';
            }}
            
            // Re-render charts to adjust text colors
            updateChartsTheme();
        }}

        function updateChartsTheme() {{
            const textColor = currentTheme === 'dark' ? '#9ca3af' : '#64748b';
            const gridColor = currentTheme === 'dark' ? '#1f2937' : '#e2e8f0';

            const updateChartConfig = (chart) => {{
                if (!chart) return;
                if (chart.config.type === 'radar') {{
                    chart.options.scales.r.grid.color = gridColor;
                    chart.options.scales.r.angleLines.color = gridColor;
                    chart.options.scales.r.pointLabels.color = textColor;
                }} else if (chart.options.scales) {{
                    if (chart.options.scales.x) {{
                        chart.options.scales.x.grid.color = gridColor;
                        chart.options.scales.x.ticks.color = textColor;
                    }}
                    if (chart.options.scales.y) {{
                        chart.options.scales.y.grid.color = gridColor;
                        chart.options.scales.y.ticks.color = textColor;
                    }}
                }}
                chart.update();
            }};

            updateChartConfig(chartIndicators);
            updateChartConfig(chartRatings);
            updateChartConfig(chartVillages);
            updateChartConfig(chartTrends);
            updateChartConfig(chartVillageRadar);
        }}

        // Populate dynamic lists in filters
        function populateFilterOptions() {{
            const filterVillage = document.getElementById('filter-village');
            const filterEnumerator = document.getElementById('filter-enumerator');

            const villages = [...new Set(dataset.map(r => r.village))].sort();
            const enumerators = [...new Set(dataset.map(r => r.enumerator))].sort();

            villages.forEach(v => {{
                const opt = document.createElement('option');
                opt.value = v;
                opt.textContent = v;
                filterVillage.appendChild(opt);
            }});

            enumerators.forEach(e => {{
                const opt = document.createElement('option');
                opt.value = e;
                opt.textContent = e;
                filterEnumerator.appendChild(opt);
            }});
        }}

        // Filters and Table handling
        function handleFilterChange() {{
            const searchVal = document.getElementById('table-search').value.toLowerCase();
            const villageVal = document.getElementById('filter-village').value;
            const enumVal = document.getElementById('filter-enumerator').value;
            const piiVal = document.getElementById('filter-pii').value;

            filteredData = dataset.filter(r => {{
                const searchMatch = !searchVal || 
                    r.id.toString().includes(searchVal) ||
                    r.hh_head.toLowerCase().includes(searchVal) ||
                    r.respondent.toLowerCase().includes(searchVal) ||
                    r.village.toLowerCase().includes(searchVal) ||
                    r.enumerator.toLowerCase().includes(searchVal) ||
                    r.phone.includes(searchVal);
                
                const villageMatch = !villageVal || r.village === villageVal;
                const enumMatch = !enumVal || r.enumerator === enumVal;
                
                let piiMatch = true;
                if (piiVal === 'has_pii') {{
                    piiMatch = r.has_pii;
                }} else if (piiVal === 'no_pii') {{
                    piiMatch = !r.has_pii;
                }}

                return searchMatch && villageMatch && enumMatch && piiMatch;
            }});

            currentPage = 1;
            renderTable();
        }}

        function clearFilters() {{
            document.getElementById('table-search').value = '';
            document.getElementById('filter-village').value = '';
            document.getElementById('filter-enumerator').value = '';
            document.getElementById('filter-pii').value = '';
            filteredData = [...dataset];
            currentPage = 1;
            renderTable();
        }}

        function handleSort(column) {{
            if (sortColumn === column) {{
                sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
            }} else {{
                sortColumn = column;
                sortDirection = 'asc';
            }}

            const thList = document.querySelectorAll('th');
            thList.forEach(th => th.className = '');

            const clickedTh = event.currentTarget;
            clickedTh.className = sortDirection === 'asc' ? 'sorted-asc' : 'sorted-desc';

            filteredData.sort((a, b) => {{
                let valA = a[column];
                let valB = b[column];

                if (typeof valA === 'string') {{
                    valA = valA.toLowerCase();
                    valB = valB.toLowerCase();
                }}

                if (valA < valB) return sortDirection === 'asc' ? -1 : 1;
                if (valA > valB) return sortDirection === 'asc' ? 1 : -1;
                return 0;
            }});

            currentPage = 1;
            renderTable();
        }}

        function renderTable() {{
            const tbody = document.getElementById('survey-table-body');
            tbody.innerHTML = '';

            const startIdx = (currentPage - 1) * rowsPerPage;
            const endIdx = Math.min(startIdx + rowsPerPage, filteredData.length);
            const paginatedData = filteredData.slice(startIdx, endIdx);

            paginatedData.forEach(r => {{
                const tr = document.createElement('tr');
                
                const hhHeadName = isSecureMode ? maskName(r.hh_head) : r.hh_head;
                const respName = isSecureMode ? maskName(r.respondent) : r.respondent;
                const formattedNotes = formatRemarks(r.remarks_html, isSecureMode);

                tr.innerHTML = `
                    <td><strong>#${{r.id}}</strong></td>
                    <td>${{hhHeadName}}</td>
                    <td>${{respName}}</td>
                    <td>${{r.village}}</td>
                    <td>${{r.enumerator}}</td>
                    <td>${{r.duration}} mins</td>
                    <td><div style="max-width: 320px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${{formattedNotes}}</div></td>
                    <td>
                        <button class="btn-view" onclick="viewDetails(${{r.id}})">
                            <i class="fa-solid fa-eye"></i> View
                        </button>
                    </td>
                `;
                tbody.appendChild(tr);
            }});

            // Update info
            const total = filteredData.length;
            document.getElementById('pagination-info').textContent = total > 0
                ? `Showing ${{startIdx + 1}} to ${{endIdx}} of ${{total}} entries`
                : 'No entries match';

            document.getElementById('btn-prev-page').disabled = currentPage === 1;
            document.getElementById('btn-next-page').disabled = endIdx >= total;
        }}

        function prevPage() {{
            if (currentPage > 1) {{
                currentPage--;
                renderTable();
            }}
        }}

        function nextPage() {{
            const total = filteredData.length;
            if (currentPage * rowsPerPage < total) {{
                currentPage++;
                renderTable();
            }}
        }}

        // Details Modal
        function viewDetails(surveyId) {{
            const r = dataset.find(x => x.id === surveyId);
            if (!r) return;

            document.getElementById('modal-title-text').textContent = `Household Survey Profile #${{r.id}}`;
            document.getElementById('modal-subtitle-text').textContent = `UUID: ${{r.uuid}} • Submission: ${{r.submission_time}}`;

            // Mask PII according to state
            document.getElementById('detail-head').textContent = isSecureMode ? maskName(r.hh_head) : r.hh_head;
            document.getElementById('detail-respondent').textContent = isSecureMode ? maskName(r.respondent) : r.respondent;
            document.getElementById('detail-phone').textContent = isSecureMode ? maskPhone(r.phone) : r.phone;
            document.getElementById('detail-ration').textContent = isSecureMode ? maskRationCard(r.ration_card) : r.ration_card;
            document.getElementById('detail-gps').textContent = maskGPS(r.lat, r.lon, isSecureMode);

            document.getElementById('detail-village').textContent = r.village;
            document.getElementById('detail-enumerator').textContent = r.enumerator;
            document.getElementById('detail-start').textContent = r.start.replace('T', ' ');
            document.getElementById('detail-end').textContent = r.end.replace('T', ' ');
            document.getElementById('detail-duration').textContent = `${{r.duration}} minutes`;

            // Remarks HTML
            document.getElementById('detail-remarks-body').innerHTML = formatRemarks(r.remarks_html, isSecureMode);

            // Populate Questions List
            const listContainer = document.getElementById('detail-indicators-list');
            listContainer.innerHTML = '';

            Object.keys(questionLabels).forEach(key => {{
                const cfg = questionLabels[key];
                const value = r.indicators[key];
                
                const item = document.createElement('div');
                item.className = 'indicator-item';

                let badgeHtml = '';
                if (cfg.type === 'score') {{
                    const percent = value * 10;
                    let colorClass = 'badge-poor';
                    if (value >= 7) colorClass = 'badge-good';
                    else if (value >= 4) colorClass = 'badge-average';

                    badgeHtml = `<span class="badge ${{colorClass}}">${{value}} / 10</span>`;
                }} else if (cfg.type === 'rating') {{
                    let colorClass = 'badge-poor';
                    if (value === 'Good') colorClass = 'badge-good';
                    else if (value === 'Average') colorClass = 'badge-average';

                    badgeHtml = `<span class="badge ${{colorClass}}">${{value}}</span>`;
                }} else {{
                    let colorClass = 'badge-poor';
                    if (value === 'Yes') colorClass = 'badge-good';
                    else if (value === 'Sometimes') colorClass = 'badge-average';

                    badgeHtml = `<span class="badge ${{colorClass}}">${{value}}</span>`;
                }}

                item.innerHTML = `
                    <div class="indicator-item-info">
                        <h5>[${{key.toUpperCase()}}] ${{cfg.label}}</h5>
                        <p>${{cfg.desc}}</p>
                    </div>
                    ${{badgeHtml}}
                `;
                listContainer.appendChild(item);
            }});

            document.getElementById('detail-modal').style.display = 'flex';
        }}

        function closeModal(event) {{
            document.getElementById('detail-modal').style.display = 'none';
        }}

        // Map Setup
        function initMap() {{
            leafMap = L.map('map-container').setView([21.5, 80.0], 5);
            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                attribution: '&copy; OpenStreetMap contributors'
            }}).addTo(leafMap);
            markerLayer = L.layerGroup().addTo(leafMap);
        }}

        function updateMapMarkers() {{
            if (!leafMap || !markerLayer) return;
            markerLayer.clearLayers();

            const markers = [];
            filteredData.forEach(r => {{
                // Coarsen coordinates if secure mode is enabled
                let markerLat = r.lat;
                let markerLon = r.lon;
                if (isSecureMode) {{
                    markerLat = Math.round(r.lat * 100) / 100;
                    markerLon = Math.round(r.lon * 100) / 100;
                }}

                const headName = isSecureMode ? maskName(r.hh_head) : r.hh_head;
                const remarksText = formatRemarks(r.remarks_html, isSecureMode);

                const popupContent = `
                    <div style="font-family: 'Inter', sans-serif; font-size: 0.8rem; line-height:1.4;">
                        <strong>Survey ID: #${{r.id}}</strong><br>
                        Household Head: ${{headName}}<br>
                        Village: ${{r.village}}<br>
                        Enumerator: ${{r.enumerator}}<br>
                        Duration: ${{r.duration}} mins<br>
                        <div style="margin-top: 6px; border-top: 1px solid #ddd; padding-top: 4px;">
                            <em>${{remarksText}}</em>
                        </div>
                    </div>
                `;

                // Render marker
                const marker = L.marker([markerLat, markerLon])
                    .bindPopup(popupContent);
                
                markerLayer.addLayer(marker);
                markers.push(marker);
            }});

            // Adjust bounds
            if (markers.length > 0) {{
                const group = new L.featureGroup(markers);
                leafMap.fitBounds(group.getBounds().pad(0.1));
            }}
        }}

        // Enumerator Cards
        function renderEnumeratorCards() {{
            const container = document.getElementById('enum-cards-container');
            container.innerHTML = '';

            const enums = [...new Set(dataset.map(r => r.enumerator))].sort();
            
            enums.forEach(eName => {{
                const enumSurveys = dataset.filter(r => r.enumerator === eName);
                const count = enumSurveys.length;
                const avgDur = Math.round(enumSurveys.reduce((sum, r) => sum + r.duration, 0) / count);
                const piiLeakCount = enumSurveys.filter(r => r.has_pii).length;
                const piiLeakRate = Math.round((piiLeakCount / count) * 100);
                
                const initials = eName.split(" ").map(w => w[0]).join("").substring(0,2).toUpperCase();

                const card = document.createElement('div');
                card.className = 'enum-card';
                card.innerHTML = `
                    <div class="enum-header">
                        <div class="enum-avatar">${{initials}}</div>
                        <div class="enum-meta">
                            <h4>${{eName}}</h4>
                            <p>Field Enumerator</p>
                        </div>
                    </div>
                    <div class="enum-stats-grid">
                        <div>
                            <div class="enum-stat-val" style="color: var(--primary-color);">${{count}}</div>
                            <div class="enum-stat-lbl">Surveys</div>
                        </div>
                        <div>
                            <div class="enum-stat-val" style="color: var(--accent-color);">${{avgDur}}m</div>
                            <div class="enum-stat-lbl">Avg Time</div>
                        </div>
                        <div>
                            <div class="enum-stat-val" style="color: var(--danger-color);">${{piiLeakRate}}%</div>
                            <div class="enum-stat-lbl">PII Rate</div>
                        </div>
                    </div>
                    <div style="font-size: 0.75rem; color: var(--text-secondary);">
                        <i class="fa-solid fa-map-location-dot"></i> Villages covered: ${{ [...new Set(enumSurveys.map(r => r.village))].join(", ") }}
                    </div>
                `;
                container.appendChild(card);
            }});
        }}

        // Village Profile View
        function loadVillageProfile(villageName) {{
            const vSurveys = dataset.filter(r => r.village === villageName);
            const total = vSurveys.length;
            const avgDur = Math.round(vSurveys.reduce((sum, r) => sum + r.duration, 0) / total);
            const enumerators = new Set(vSurveys.map(r => r.enumerator)).size;
            
            // Re-fill village KPIs
            const grid = document.getElementById('village-kpi-grid');
            grid.innerHTML = `
                <div class="kpi-card surveys">
                    <div class="kpi-info">
                        <h3>Village Surveys</h3>
                        <div class="kpi-value">${{total}}</div>
                        <div class="kpi-subtext">Completed forms</div>
                    </div>
                    <div class="kpi-icon"><i class="fa-solid fa-clipboard-check"></i></div>
                </div>
                <div class="kpi-card duration">
                    <div class="kpi-info">
                        <h3>Avg Interview Time</h3>
                        <div class="kpi-value">${{avgDur}}m</div>
                        <div class="kpi-subtext">Duration in village</div>
                    </div>
                    <div class="kpi-icon"><i class="fa-solid fa-clock"></i></div>
                </div>
                <div class="kpi-card enumerators">
                    <div class="kpi-info">
                        <h3>Active Surveyors</h3>
                        <div class="kpi-value">${{enumerators}}</div>
                        <div class="kpi-subtext">Different investigators</div>
                    </div>
                    <div class="kpi-icon"><i class="fa-solid fa-route"></i></div>
                </div>
            `;

            // Radar Chart for Village Indicators
            const numericKeys = ["q01", "q04", "q07", "q10", "q13", "q16", "q19", "q22", "q25"];
            const averages = numericKeys.map(key => {{
                const sum = vSurveys.reduce((acc, r) => acc + r.indicators[key], 0);
                return Math.round((sum / total) * 10) / 10;
            }});

            const labels = numericKeys.map(key => questionLabels[key].label);

            if (chartVillageRadar) {{
                chartVillageRadar.data.labels = labels;
                chartVillageRadar.data.datasets[0].label = `${{villageName}} averages`;
                chartVillageRadar.data.datasets[0].data = averages;
                chartVillageRadar.update();
            }} else {{
                const ctx = document.getElementById('chart-village-radar').getContext('2d');
                chartVillageRadar = new Chart(ctx, {{
                    type: 'radar',
                    data: {{
                        labels: labels,
                        datasets: [{{
                            label: `${{villageName}} averages`,
                            data: averages,
                            backgroundColor: 'rgba(99, 102, 241, 0.2)',
                            borderColor: '#6366f1',
                            pointBackgroundColor: '#6366f1',
                            pointBorderColor: '#fff',
                            borderWidth: 2
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{ position: 'top', labels: {{ color: '#9ca3af' }} }}
                        }},
                        scales: {{
                            r: {{
                                grid: {{ color: '#1f2937' }},
                                angleLines: {{ color: '#1f2937' }},
                                pointLabels: {{ color: '#9ca3af', font: {{ size: 10 }} }},
                                min: 0,
                                max: 10,
                                ticks: {{ stepSize: 2, color: '#9ca3af', backdropColor: 'transparent' }}
                            }}
                        }}
                    }}
                }});
            }}
            updateChartsTheme();
        }}

        // Main Charts Implementation
        function initCharts() {{
            const textColor = '#9ca3af';
            const gridColor = '#1f2937';

            // Chart 1: Average Performance Indicators Radar
            const numericKeys = ["q01", "q04", "q07", "q10", "q13", "q16", "q19", "q22", "q25"];
            const overallAverages = numericKeys.map(key => {{
                const sum = dataset.reduce((acc, r) => acc + r.indicators[key], 0);
                return Math.round((sum / dataset.length) * 10) / 10;
            }});
            const labels = numericKeys.map(key => questionLabels[key].label);

            const ctx1 = document.getElementById('chart-indicators').getContext('2d');
            chartIndicators = new Chart(ctx1, {{
                type: 'radar',
                data: {{
                    labels: labels,
                    datasets: [{{
                        label: 'All Households Average Score (0-10)',
                        data: overallAverages,
                        backgroundColor: 'rgba(6, 182, 212, 0.2)',
                        borderColor: '#06b6d4',
                        pointBackgroundColor: '#06b6d4',
                        pointBorderColor: '#fff',
                        borderWidth: 2
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{ position: 'top', labels: {{ color: textColor }} }}
                    }},
                    scales: {{
                        r: {{
                            grid: {{ color: gridColor }},
                            angleLines: {{ color: gridColor }},
                            pointLabels: {{ color: textColor, font: {{ size: 9 }} }},
                            min: 0,
                            max: 10,
                            ticks: {{ stepSize: 2, color: textColor, backdropColor: 'transparent' }}
                        }}
                    }}
                }}
            }});

            // Chart 2: Ratings Stacked Bar Chart
            const ratingKeys = ["q02", "q05", "q08", "q11", "q14", "q17", "q20", "q23"];
            const ratingLabels = ratingKeys.map(key => questionLabels[key].label);
            const goodData = [];
            const avgData = [];
            const poorData = [];

            ratingKeys.forEach(key => {{
                let good = 0, avg = 0, poor = 0;
                dataset.forEach(r => {{
                    const val = r.indicators[key];
                    if (val === 'Good') good++;
                    else if (val === 'Average') avg++;
                    else if (val === 'Poor') poor++;
                }});
                goodData.push(good);
                avgData.push(avg);
                poorData.push(poor);
            }});

            const ctx2 = document.getElementById('chart-ratings').getContext('2d');
            chartRatings = new Chart(ctx2, {{
                type: 'bar',
                data: {{
                    labels: ratingLabels,
                    datasets: [
                        {{ label: 'Good', data: goodData, backgroundColor: '#10b981' }},
                        {{ label: 'Average', data: avgData, backgroundColor: '#f59e0b' }},
                        {{ label: 'Poor', data: poorData, backgroundColor: '#ef4444' }}
                    ]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{ position: 'top', labels: {{ color: textColor }} }}
                    }},
                    scales: {{
                        x: {{ stacked: true, grid: {{ color: gridColor }}, ticks: {{ color: textColor, font: {{ size: 8 }} }} }},
                        y: {{ stacked: true, grid: {{ color: gridColor }}, ticks: {{ color: textColor }} }}
                    }}
                }}
            }});

            // Chart 3: Village Completion Doughnut
            const villageCounts = {{}};
            dataset.forEach(r => {{
                villageCounts[r.village] = (villageCounts[r.village] || 0) + 1;
            }});

            const ctx3 = document.getElementById('chart-villages').getContext('2d');
            chartVillages = new Chart(ctx3, {{
                type: 'doughnut',
                data: {{
                    labels: Object.keys(villageCounts),
                    datasets: [{{
                        data: Object.values(villageCounts),
                        backgroundColor: [
                            '#6366f1', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', 
                            '#8b5cf6', '#ec4899', '#3b82f6', '#14b8a6', '#f97316'
                        ],
                        borderWidth: 1,
                        borderColor: '#111827'
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{ position: 'right', labels: {{ color: textColor, font: {{ size: 9 }} }} }}
                    }}
                }}
            }});

            // Chart 4: Time Trend Line Chart
            const surveyDates = dataset.map(r => r.start.split('T')[0]);
            const dateCounts = {{}};
            surveyDates.forEach(d => {{
                dateCounts[d] = (dateCounts[d] || 0) + 1;
            }});

            const sortedDates = Object.keys(dateCounts).sort();
            const cumulativeCounts = [];
            let runningSum = 0;
            sortedDates.forEach(d => {{
                runningSum += dateCounts[d];
                cumulativeCounts.push(runningSum);
            }});

            const ctx4 = document.getElementById('chart-trends').getContext('2d');
            chartTrends = new Chart(ctx4, {{
                type: 'line',
                data: {{
                    labels: sortedDates.map(d => d.substring(5)),
                    datasets: [{{
                        label: 'Total Completed Surveys (Cumulative)',
                        data: cumulativeCounts,
                        borderColor: '#6366f1',
                        backgroundColor: 'rgba(99, 102, 241, 0.1)',
                        fill: true,
                        tension: 0.3,
                        borderWidth: 2
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{ position: 'top', labels: {{ color: textColor }} }}
                    }},
                    scales: {{
                        x: {{ grid: {{ color: gridColor }}, ticks: {{ color: textColor, maxTicksLimit: 12 }} }},
                        y: {{ grid: {{ color: gridColor }}, ticks: {{ color: textColor }} }}
                    }}
                }}
            }});
        }}

        // Export data to CSV
        function exportCSV() {{
            const headers = [
                "Survey ID", "UUID", "Start Time", "End Time", "Duration (mins)", 
                "Enumerator", "Household Head", "Respondent", "Phone", 
                "Village", "GPS Lat", "GPS Lon", "Ration Card No", 
                ...Object.keys(questionLabels), "Remarks", "Submission Time"
            ];

            const rows = filteredData.map(r => {{
                const head = isSecureMode ? maskName(r.hh_head) : r.hh_head;
                const resp = isSecureMode ? maskName(r.respondent) : r.respondent;
                const phone = isSecureMode ? maskPhone(r.phone) : r.phone;
                const card = isSecureMode ? maskRationCard(r.ration_card) : r.ration_card;
                const lat = isSecureMode ? Math.round(r.lat * 100) / 100 : r.lat;
                const lon = isSecureMode ? Math.round(r.lon * 100) / 100 : r.lon;
                
                // Format remarks
                let remarks = r.remarks_raw;
                if (isSecureMode) {{
                    const temp = document.createElement('div');
                    temp.innerHTML = r.remarks_html;
                    temp.querySelectorAll('.pii-span').forEach(span => {{
                        span.textContent = `[REDACTED: ${{span.getAttribute('data-class').replace('_', ' ')}}]`;
                    }});
                    remarks = temp.textContent;
                }}

                return [
                    r.id, r.uuid, r.start, r.end, r.duration,
                    r.enumerator, head, resp, phone,
                    r.village, lat, lon, card,
                    ...Object.keys(questionLabels).map(k => r.indicators[k]),
                    remarks, r.submission_time
                ];
            }});

            let csvContent = "data:text/csv;charset=utf-8,";
            csvContent += headers.map(h => `"${{h}}"`).join(",") + "\\n";
            
            rows.forEach(row => {{
                csvContent += row.map(v => `"${{v.toString().replace(/"/g, '""')}}"`).join(",") + "\\n";
            }});

            const encodedUri = encodeURI(csvContent);
            const link = document.createElement("a");
            link.setAttribute("href", encodedUri);
            link.setAttribute("download", `household_survey_export_${{isSecureMode ? 'secure' : 'raw'}}.csv`);
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }}
    </script>
</body>
</html>
"""

    # Write HTML
    output_path = '/home/desinotorious/src/github.com/bprashanth/io/benchmarks/pii/corpus/household_dashboard.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"Success! Dashboard compiled successfully to: {output_path}")

if __name__ == '__main__':
    build()
