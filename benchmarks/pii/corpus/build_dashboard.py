import pandas as pd
import json
import os

def build():
    csv_path = '/home/desinotorious/src/github.com/bprashanth/io/benchmarks/pii/corpus/scholarship_applicants.csv'
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return

    # Read CSV
    df = pd.read_csv(csv_path)

    # Handle numeric columns cleanly
    df['Family Income'] = pd.to_numeric(df['Family Income'], errors='coerce').fillna(0).astype(int)
    df['Marks %'] = pd.to_numeric(df['Marks %'], errors='coerce').fillna(0.0).astype(float)
    df['DOB'] = pd.to_numeric(df['DOB'], errors='coerce').fillna(0).astype(int)
    df['Umar'] = pd.to_numeric(df['Umar'], errors='coerce').fillna(0).astype(int)
    df['Sr No'] = pd.to_numeric(df['Sr No'], errors='coerce').fillna(0).astype(int)

    # Replace NaN remarks with empty string
    df['Remarks'] = df['Remarks'].fillna('').astype(str)

    # Scheme values dictionary for financial analysis
    scheme_funds = {
        "Post-Matric Scholarship Scheme": 10000,
        "Merit-cum-Means Scholarship": 15000,
        "EBC Scholarship Scheme": 8000,
        "Minority Welfare Scholarship": 12000,
        "Savitribai Phule Scholarship": 7000,
        "Pre-Matric Scholarship Scheme": 4000,
        "Rajarshi Shahu Maharaj Scholarship": 11000
    }

    # Generate records list
    records = []
    for _, row in df.iterrows():
        scheme = str(row['Name of scheme'])
        fund = scheme_funds.get(scheme, 10000)
        records.append({
            'id': int(row['Sr No']),
            'name': str(row['Naam']),
            'father_name': str(row['Pita ka naam']),
            'dob': int(row['DOB']),
            'age': int(row['Umar']),
            'phone': str(row['Mob']),
            'alt_phone': str(row['Alt Contact']),
            'aadhar': str(row['Aadhar No']),
            'school': str(row['School']),
            'village': str(row['Gaon']),
            'taluka': str(row['Taluka']),
            'district': str(row['District']),
            'category': str(row['Category']),
            'income': int(row['Family Income']),
            'marks': float(row['Marks %']),
            'status': str(row['Status']),
            'remarks': str(row['Remarks']),
            'bank_account': str(row['col_17']),
            'ifsc': str(row['IFSC']),
            'scheme': scheme,
            'amount': fund
        })

    # Prepare JSON data
    json_data = json.dumps(records, indent=2)

    # HTML Template
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VidyaDaan Scholar Dashboard</title>
    <!-- Outfit & Inter Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <!-- FontAwesome CDN for Icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <!-- Chart.js CDN -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-tertiary: #334155;
            --bg-hover: #475569;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --border-color: #334155;
            --primary-color: #6366f1;
            --primary-glow: rgba(99, 102, 241, 0.15);
            --accent-color: #06b6d4;
            --success-color: #10b981;
            --success-glow: rgba(16, 185, 129, 0.15);
            --warning-color: #f59e0b;
            --warning-glow: rgba(245, 158, 11, 0.15);
            --danger-color: #ef4444;
            --danger-glow: rgba(239, 68, 68, 0.15);
            --info-color: #3b82f6;
            --info-glow: rgba(59, 130, 246, 0.15);
            --card-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2), 0 2px 4px -2px rgba(0, 0, 0, 0.2);
            --font-display: 'Outfit', sans-serif;
            --font-body: 'Inter', sans-serif;
        }}

        body.light-theme {{
            --bg-primary: #f8fafc;
            --bg-secondary: #ffffff;
            --bg-tertiary: #e2e8f0;
            --bg-hover: #cbd5e1;
            --text-primary: #0f172a;
            --text-secondary: #475569;
            --border-color: #cbd5e1;
            --primary-color: #4f46e5;
            --primary-glow: rgba(79, 70, 229, 0.1);
            --accent-color: #0891b2;
            --success-color: #059669;
            --success-glow: rgba(5, 150, 105, 0.1);
            --warning-color: #d97706;
            --warning-glow: rgba(217, 119, 6, 0.1);
            --danger-color: #dc2626;
            --danger-glow: rgba(220, 38, 38, 0.1);
            --info-color: #2563eb;
            --info-glow: rgba(37, 99, 235, 0.1);
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

        /* Sidebar Styling */
        aside {{
            width: 260px;
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
        }}

        .brand {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 32px;
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

        .nav-links {{
            display: flex;
            flex-direction: column;
            gap: 8px;
            list-style: none;
            flex: 1;
        }}

        .nav-item {{
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 16px;
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
            padding-left: 12px;
            background-color: var(--primary-glow);
            color: var(--primary-color);
        }}

        .nav-item i {{
            font-size: 1.15rem;
            width: 24px;
            text-align: center;
        }}

        .sidebar-footer {{
            margin-top: auto;
            display: flex;
            flex-direction: column;
            gap: 16px;
        }}

        .theme-toggle-btn {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 12px;
            border-radius: 8px;
            background-color: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            cursor: pointer;
            font-weight: 600;
            transition: all 0.2s;
        }}

        .theme-toggle-btn:hover {{
            background-color: var(--bg-hover);
        }}

        /* Main Workspace */
        main {{
            flex: 1;
            margin-left: 260px;
            padding: 40px;
            max-width: 1400px;
            width: calc(100% - 260px);
        }}

        /* Header block */
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 32px;
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

        .header-actions {{
            display: flex;
            align-items: center;
            gap: 16px;
        }}

        .refresh-btn {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 10px 16px;
            border-radius: 8px;
            background-color: var(--primary-color);
            border: none;
            color: white;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }}

        .refresh-btn:hover {{
            background-color: var(--primary-hover);
            transform: translateY(-1px);
        }}

        /* KPI Cards Grid */
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
            margin-bottom: 32px;
        }}

        .kpi-card {{
            background-color: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 24px;
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

        .kpi-card.disbursed::after {{ --accent: var(--success-color); }}
        .kpi-card.approved::after {{ --accent: var(--info-color); }}
        .kpi-card.pending::after {{ --accent: var(--warning-color); }}
        .kpi-card.rejected::after {{ --accent: var(--danger-color); }}
        .kpi-card.total::after {{ --accent: var(--primary-color); }}
        .kpi-card.marks::after {{ --accent: #8b5cf6; }}
        .kpi-card.income::after {{ --accent: #ec4899; }}

        .kpi-info h3 {{
            font-size: 0.85rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }}

        .kpi-value {{
            font-family: var(--font-display);
            font-size: 1.8rem;
            font-weight: 700;
            line-height: 1.2;
            margin-bottom: 4px;
        }}

        .kpi-subtext {{
            font-size: 0.75rem;
            color: var(--text-secondary);
            display: flex;
            align-items: center;
            gap: 4px;
        }}

        .kpi-icon {{
            width: 44px;
            height: 44px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.3rem;
        }}

        .total .kpi-icon {{ background-color: var(--primary-glow); color: var(--primary-color); }}
        .disbursed .kpi-icon {{ background-color: var(--success-glow); color: var(--success-color); }}
        .approved .kpi-icon {{ background-color: var(--info-glow); color: var(--info-color); }}
        .pending .kpi-icon {{ background-color: var(--warning-glow); color: var(--warning-color); }}
        .rejected .kpi-icon {{ background-color: var(--danger-glow); color: var(--danger-color); }}
        .marks .kpi-icon {{ background-color: rgba(139, 92, 246, 0.15); color: #8b5cf6; }}
        .income .kpi-icon {{ background-color: rgba(236, 72, 153, 0.15); color: #ec4899; }}

        /* Charts Section */
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 24px;
            margin-bottom: 32px;
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
            padding: 24px;
            box-shadow: var(--card-shadow);
            display: flex;
            flex-direction: column;
        }}

        .chart-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }}

        .chart-title {{
            font-family: var(--font-display);
            font-size: 1.1rem;
            font-weight: 600;
        }}

        .chart-container {{
            position: relative;
            flex: 1;
            min-height: 280px;
            max-height: 350px;
        }}

        /* Table & Filters Section */
        .data-section {{
            background-color: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            box-shadow: var(--card-shadow);
            overflow: hidden;
            margin-bottom: 32px;
        }}

        .filters-panel {{
            padding: 24px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            gap: 16px;
            background-color: rgba(0, 0, 0, 0.05);
        }}

        .search-row {{
            display: flex;
            gap: 16px;
        }}

        .search-box-container {{
            position: relative;
            flex: 1;
        }}

        .search-box-container i {{
            position: absolute;
            left: 16px;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-secondary);
        }}

        .search-input {{
            width: 100%;
            padding: 12px 16px 12px 48px;
            border-radius: 8px;
            background-color: var(--bg-primary);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            outline: none;
            font-size: 0.95rem;
            transition: all 0.2s;
        }}

        .search-input:focus {{
            border-color: var(--primary-color);
            box-shadow: 0 0 0 2px var(--primary-glow);
        }}

        .filter-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            align-items: center;
        }}

        .filter-select {{
            padding: 10px 16px;
            border-radius: 8px;
            background-color: var(--bg-primary);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            outline: none;
            font-size: 0.85rem;
            min-width: 150px;
            cursor: pointer;
            transition: all 0.2s;
        }}

        .filter-select:focus {{
            border-color: var(--primary-color);
        }}

        .clear-filters-btn {{
            padding: 10px 16px;
            border-radius: 8px;
            background-color: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            cursor: pointer;
            font-weight: 500;
            font-size: 0.85rem;
            transition: all 0.2s;
        }}

        .clear-filters-btn:hover {{
            background-color: var(--bg-hover);
        }}

        .active-filters {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            align-items: center;
        }}

        .active-filter-badge {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 4px 12px;
            background-color: var(--primary-glow);
            color: var(--primary-color);
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
        }}

        .active-filter-badge i {{
            cursor: pointer;
        }}

        /* Table Styling */
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
            background-color: rgba(0, 0, 0, 0.1);
            padding: 16px 24px;
            color: var(--text-secondary);
            font-weight: 600;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 1px solid var(--border-color);
            cursor: pointer;
            user-select: none;
            transition: background-color 0.2s;
        }}

        th:hover {{
            background-color: rgba(0, 0, 0, 0.2);
        }}

        th.sorted-asc::after {{
            content: ' \2191';
        }}

        th.sorted-desc::after {{
            content: ' \2193';
        }}

        td {{
            padding: 16px 24px;
            border-bottom: 1px solid var(--border-color);
            font-size: 0.9rem;
            vertical-align: middle;
        }}

        tr:last-child td {{
            border-bottom: none;
        }}

        tr:hover td {{
            background-color: rgba(255, 255, 255, 0.02);
        }}
        body.light-theme tr:hover td {{
            background-color: rgba(0, 0, 0, 0.02);
        }}

        /* Badges */
        .badge {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 10px;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }}

        .badge-disbursed {{ background-color: var(--success-glow); color: var(--success-color); }}
        .badge-approved {{ background-color: var(--info-glow); color: var(--info-color); }}
        .badge-review {{ background-color: var(--warning-glow); color: var(--warning-color); }}
        .badge-pending {{ background-color: rgba(139, 92, 246, 0.15); color: #8b5cf6; }}
        .badge-rejected {{ background-color: var(--danger-glow); color: var(--danger-color); }}

        /* Action Buttons */
        .btn-view {{
            background-color: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 0.8rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}

        .btn-view:hover {{
            background-color: var(--bg-hover);
            border-color: var(--primary-color);
        }}

        /* Pagination controls */
        .pagination-bar {{
            padding: 16px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-top: 1px solid var(--border-color);
            background-color: rgba(0, 0, 0, 0.05);
        }}

        .pagination-info {{
            font-size: 0.85rem;
            color: var(--text-secondary);
        }}

        .pagination-controls {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .page-btn {{
            padding: 8px 12px;
            border-radius: 6px;
            border: 1px solid var(--border-color);
            background-color: var(--bg-primary);
            color: var(--text-primary);
            font-size: 0.85rem;
            cursor: pointer;
            transition: all 0.2s;
        }}

        .page-btn:hover:not(:disabled) {{
            background-color: var(--primary-color);
            color: white;
            border-color: var(--primary-color);
        }}

        .page-btn:disabled {{
            opacity: 0.5;
            cursor: not-allowed;
        }}

        .page-number {{
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 0.85rem;
            font-weight: 600;
        }}

        .page-number.active {{
            background-color: var(--primary-glow);
            color: var(--primary-color);
        }}

        /* Audit & Tasks Panel layout */
        .audit-layout {{
            display: grid;
            grid-template-columns: 280px 1fr;
            gap: 24px;
            margin-bottom: 32px;
        }}

        @media (max-width: 768px) {{
            .audit-layout {{
                grid-template-columns: 1fr;
            }}
        }}

        .audit-sidebar {{
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}

        .audit-filter-card {{
            background-color: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 16px;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .audit-filter-card:hover, .audit-filter-card.active {{
            border-color: var(--primary-color);
            background-color: var(--primary-glow);
        }}

        .audit-filter-info h4 {{
            font-family: var(--font-display);
            font-size: 0.95rem;
            font-weight: 600;
            margin-bottom: 4px;
        }}

        .audit-filter-info p {{
            font-size: 0.75rem;
            color: var(--text-secondary);
        }}

        .audit-count {{
            padding: 4px 10px;
            border-radius: 8px;
            font-weight: 700;
            font-size: 0.85rem;
        }}

        .audit-count.danger {{ background-color: var(--danger-glow); color: var(--danger-color); }}
        .audit-count.warning {{ background-color: var(--warning-glow); color: var(--warning-color); }}
        .audit-count.info {{ background-color: var(--info-glow); color: var(--info-color); }}

        .audit-content {{
            display: flex;
            flex-direction: column;
            gap: 16px;
        }}

        .audit-card {{
            background-color: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 24px;
            box-shadow: var(--card-shadow);
            position: relative;
        }}

        .audit-card-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 12px;
        }}

        .audit-card-title {{
            font-family: var(--font-display);
            font-size: 1.1rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .audit-badge {{
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: 700;
            text-transform: uppercase;
        }}

        .audit-desc {{
            color: var(--text-secondary);
            font-size: 0.85rem;
            margin-bottom: 16px;
            line-height: 1.5;
        }}

        .audit-actions {{
            display: flex;
            justify-content: flex-end;
            gap: 12px;
        }}

        /* Scheme details grid */
        .scheme-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 24px;
            margin-bottom: 32px;
        }}

        .scheme-card {{
            background-color: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 24px;
            box-shadow: var(--card-shadow);
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            transition: all 0.2s;
        }}

        .scheme-card:hover {{
            transform: translateY(-2px);
            border-color: var(--primary-color);
        }}

        .scheme-header {{
            margin-bottom: 16px;
        }}

        .scheme-title {{
            font-family: var(--font-display);
            font-size: 1.15rem;
            font-weight: 700;
            margin-bottom: 6px;
            color: var(--primary-color);
        }}

        .scheme-meta {{
            display: flex;
            justify-content: space-between;
            font-size: 0.8rem;
            color: var(--text-secondary);
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 12px;
            margin-bottom: 16px;
        }}

        .scheme-body {{
            display: flex;
            flex-direction: column;
            gap: 8px;
            margin-bottom: 16px;
        }}

        .scheme-stat-row {{
            display: flex;
            justify-content: space-between;
            font-size: 0.85rem;
        }}

        .scheme-stat-label {{
            color: var(--text-secondary);
        }}

        .scheme-stat-val {{
            font-weight: 600;
        }}

        .scheme-footer-fund {{
            padding-top: 12px;
            border-top: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .scheme-fund-label {{
            font-size: 0.8rem;
            color: var(--text-secondary);
        }}

        .scheme-fund-val {{
            font-family: var(--font-display);
            font-size: 1.2rem;
            font-weight: 700;
            color: var(--success-color);
        }}

        /* Sliding Detail Drawer */
        .drawer-overlay {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(4px);
            z-index: 1000;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.3s ease;
        }}

        .drawer-overlay.open {{
            opacity: 1;
            pointer-events: auto;
        }}

        .drawer {{
            position: fixed;
            top: 0;
            right: -600px;
            width: 600px;
            max-width: 100%;
            height: 100%;
            background-color: var(--bg-secondary);
            box-shadow: -10px 0 30px rgba(0, 0, 0, 0.3);
            z-index: 1001;
            display: flex;
            flex-direction: column;
            transition: right 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }}

        .drawer.open {{
            right: 0;
        }}

        .drawer-header {{
            padding: 24px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .drawer-title-area h3 {{
            font-family: var(--font-display);
            font-size: 1.3rem;
            font-weight: 700;
        }}

        .drawer-title-area p {{
            font-size: 0.85rem;
            color: var(--text-secondary);
            margin-top: 2px;
        }}

        .close-drawer-btn {{
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background-color: var(--bg-tertiary);
            border: none;
            color: var(--text-primary);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.1rem;
            transition: background-color 0.2s;
        }}

        .close-drawer-btn:hover {{
            background-color: var(--bg-hover);
        }}

        .drawer-tabs {{
            display: flex;
            border-bottom: 1px solid var(--border-color);
            background-color: rgba(0, 0, 0, 0.05);
        }}

        .drawer-tab {{
            flex: 1;
            padding: 12px 8px;
            text-align: center;
            border-bottom: 2px solid transparent;
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--text-secondary);
            cursor: pointer;
            transition: all 0.2s;
        }}

        .drawer-tab.active {{
            border-bottom-color: var(--primary-color);
            color: var(--primary-color);
            background-color: rgba(255, 255, 255, 0.01);
        }}

        .drawer-body {{
            flex: 1;
            overflow-y: auto;
            padding: 24px;
        }}

        .drawer-tab-content {{
            display: none;
        }}

        .drawer-tab-content.active {{
            display: block;
        }}

        .detail-group {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 16px;
            margin-bottom: 24px;
        }}

        .detail-item {{
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}

        .detail-item.full-width {{
            grid-column: span 2;
        }}

        .detail-label {{
            font-size: 0.75rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .detail-val {{
            font-size: 0.95rem;
            font-weight: 500;
        }}

        /* Action box inside Drawer */
        .drawer-action-box {{
            padding: 20px;
            border-top: 1px solid var(--border-color);
            background-color: rgba(0, 0, 0, 0.05);
        }}

        .action-form-row {{
            display: flex;
            flex-direction: column;
            gap: 8px;
            margin-bottom: 16px;
        }}

        .action-form-label {{
            font-size: 0.85rem;
            font-weight: 600;
        }}

        .action-form-select {{
            padding: 10px;
            border-radius: 6px;
            background-color: var(--bg-primary);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            font-size: 0.9rem;
        }}

        .action-form-textarea {{
            padding: 10px;
            border-radius: 6px;
            background-color: var(--bg-primary);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            font-size: 0.9rem;
            min-height: 80px;
            resize: vertical;
        }}

        .action-buttons {{
            display: flex;
            gap: 12px;
        }}

        .btn-action-primary {{
            flex: 1;
            padding: 12px;
            border-radius: 8px;
            background-color: var(--primary-color);
            border: none;
            color: white;
            font-weight: 600;
            cursor: pointer;
            transition: background-color 0.2s;
        }}

        .btn-action-primary:hover {{
            background-color: var(--primary-hover);
        }}

        .btn-notify {{
            padding: 12px 16px;
            border-radius: 8px;
            background-color: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .btn-notify:hover {{
            background-color: var(--bg-hover);
        }}

        /* Toast notifications */
        .toast-container {{
            position: fixed;
            bottom: 24px;
            right: 24px;
            display: flex;
            flex-direction: column;
            gap: 8px;
            z-index: 2000;
        }}

        .toast {{
            background-color: var(--bg-secondary);
            color: var(--text-primary);
            border-left: 4px solid var(--primary-color);
            padding: 16px 20px;
            border-radius: 8px;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
            display: flex;
            align-items: center;
            gap: 12px;
            min-width: 300px;
            animation: slideIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            border-top: 1px solid var(--border-color);
            border-right: 1px solid var(--border-color);
            border-bottom: 1px solid var(--border-color);
        }}

        .toast.success {{ border-left-color: var(--success-color); }}
        .toast.warning {{ border-left-color: var(--warning-color); }}
        .toast.danger {{ border-left-color: var(--danger-color); }}

        @keyframes slideIn {{
            from {{ transform: translateY(20px); opacity: 0; }}
            to {{ transform: translateY(0); opacity: 1; }}
        }}

        /* Hide sections */
        .content-tab {{
            display: none;
        }}

        .content-tab.active {{
            display: block;
        }}
    </style>
</head>
<body>

    <!-- Sidebar Navigation -->
    <aside>
        <div class="brand">
            <i class="fa-solid fa-graduation-cap brand-icon"></i>
            <div class="brand-name">
                <h1>VidyaDaan</h1>
                <p>Scholarship Portal</p>
            </div>
        </div>

        <ul class="nav-links">
            <li>
                <div class="nav-item active" onclick="switchTab('overview', this)">
                    <i class="fa-solid fa-chart-line"></i> Dashboard Overview
                </div>
            </li>
            <li>
                <div class="nav-item" onclick="switchTab('applications', this)">
                    <i class="fa-solid fa-users"></i> Applications Registry
                </div>
            </li>
            <li>
                <div class="nav-item" onclick="switchTab('audit', this)">
                    <i class="fa-solid fa-triangle-exclamation"></i> Tasks & Alerts
                </div>
            </li>
            <li>
                <div class="nav-item" onclick="switchTab('schemes', this)">
                    <i class="fa-solid fa-clipboard-list"></i> Scheme Details
                </div>
            </li>
        </ul>

        <div class="sidebar-footer">
            <button class="theme-toggle-btn" onclick="toggleTheme()">
                <i class="fa-solid fa-moon" id="theme-icon"></i> <span id="theme-text">Toggle Theme</span>
            </button>
        </div>
    </aside>

    <!-- Main Workspace -->
    <main>
        <!-- Dashboard Overview Tab -->
        <div id="overview" class="content-tab active">
            <header>
                <div class="page-title">
                    <h2>Dashboard Overview</h2>
                    <p>Real-time analytics and scholarship disbursement statistics</p>
                </div>
                <div class="header-actions">
                    <button class="refresh-btn" onclick="resetData()">
                        <i class="fa-solid fa-rotate-left"></i> Reset Demo Data
                    </button>
                </div>
            </header>

            <!-- KPIs -->
            <div class="kpi-grid">
                <div class="kpi-card total">
                    <div class="kpi-info">
                        <h3>Total Applications</h3>
                        <div class="kpi-value" id="kpi-total-apps">0</div>
                        <div class="kpi-subtext">Received overall</div>
                    </div>
                    <div class="kpi-icon"><i class="fa-solid fa-folder-open"></i></div>
                </div>

                <div class="kpi-card disbursed">
                    <div class="kpi-info">
                        <h3>Fund Disbursed</h3>
                        <div class="kpi-value" id="kpi-disbursed-amount">₹0</div>
                        <div class="kpi-subtext" id="kpi-disbursed-count">0 Applications</div>
                    </div>
                    <div class="kpi-icon"><i class="fa-solid fa-circle-check"></i></div>
                </div>

                <div class="kpi-card approved">
                    <div class="kpi-info">
                        <h3>Pending Disbursal</h3>
                        <div class="kpi-value" id="kpi-approved-amount">₹0</div>
                        <div class="kpi-subtext" id="kpi-approved-count">0 Approved</div>
                    </div>
                    <div class="kpi-icon"><i class="fa-solid fa-circle-arrow-up"></i></div>
                </div>

                <div class="kpi-card pending">
                    <div class="kpi-info">
                        <h3>Under Review</h3>
                        <div class="kpi-value" id="kpi-review-count">0</div>
                        <div class="kpi-subtext" id="kpi-pending-sub">0 Pending Verification</div>
                    </div>
                    <div class="kpi-icon"><i class="fa-solid fa-clock"></i></div>
                </div>

                <div class="kpi-card marks">
                    <div class="kpi-info">
                        <h3>Avg Academic Marks</h3>
                        <div class="kpi-value" id="kpi-avg-marks">0.0%</div>
                        <div class="kpi-subtext">Across all applicants</div>
                    </div>
                    <div class="kpi-icon"><i class="fa-solid fa-star"></i></div>
                </div>

                <div class="kpi-card income">
                    <div class="kpi-info">
                        <h3>Avg Family Income</h3>
                        <div class="kpi-value" id="kpi-avg-income">₹0</div>
                        <div class="kpi-subtext">Economic baseline</div>
                    </div>
                    <div class="kpi-icon"><i class="fa-solid fa-wallet"></i></div>
                </div>
            </div>

            <!-- Charts -->
            <div class="charts-grid">
                <div class="chart-card">
                    <div class="chart-header">
                        <div class="chart-title">Application Status Distribution</div>
                    </div>
                    <div class="chart-container">
                        <canvas id="statusChart"></canvas>
                    </div>
                </div>

                <div class="chart-card">
                    <div class="chart-header">
                        <div class="chart-title">Applications by Scheme</div>
                    </div>
                    <div class="chart-container">
                        <canvas id="schemeChart"></canvas>
                    </div>
                </div>

                <div class="chart-card" style="grid-column: span 2;">
                    <div class="chart-header">
                        <div class="chart-title">Applicant Profile: Academic Marks % vs. Family Annual Income</div>
                    </div>
                    <div class="chart-container" style="max-height: 400px; min-height: 350px;">
                        <canvas id="scatterChart"></canvas>
                    </div>
                </div>
            </div>
        </div>

        <!-- Applications Tab -->
        <div id="applications" class="content-tab">
            <header>
                <div class="page-title">
                    <h2>Applications Registry</h2>
                    <p>Search, filter, and review individual scholarship requests</p>
                </div>
            </header>

            <div class="data-section">
                <!-- Filters -->
                <div class="filters-panel">
                    <div class="search-row">
                        <div class="search-box-container">
                            <i class="fa-solid fa-magnifying-glass"></i>
                            <input type="text" class="search-input" id="search-box" placeholder="Search by name, school, village, Aadhaar, scheme..." oninput="applyFilters()">
                        </div>
                    </div>
                    <div class="filter-row">
                        <select class="filter-select" id="filter-status" onchange="applyFilters()">
                            <option value="">All Statuses</option>
                            <option value="Disbursed">Disbursed</option>
                            <option value="Approved">Approved</option>
                            <option value="Under Review">Under Review</option>
                            <option value="Pending">Pending</option>
                            <option value="Rejected">Rejected</option>
                        </select>

                        <select class="filter-select" id="filter-scheme" onchange="applyFilters()">
                            <option value="">All Schemes</option>
                        </select>

                        <select class="filter-select" id="filter-taluka" onchange="applyFilters()">
                            <option value="">All Talukas</option>
                        </select>

                        <select class="filter-select" id="filter-district" onchange="applyFilters()">
                            <option value="">All Districts</option>
                        </select>

                        <select class="filter-select" id="filter-category" onchange="applyFilters()">
                            <option value="">All Categories</option>
                        </select>

                        <button class="clear-filters-btn" onclick="clearFilters()">
                            <i class="fa-solid fa-filter-circle-xmark"></i> Clear
                        </button>
                    </div>
                    <div class="active-filters" id="active-filters-list"></div>
                </div>

                <!-- Table -->
                <div class="table-responsive">
                    <table id="applicants-table">
                        <thead>
                            <tr>
                                <th onclick="sortData('id')" id="th-id">Sr No</th>
                                <th onclick="sortData('name')" id="th-name">Applicant</th>
                                <th onclick="sortData('scheme')" id="th-scheme">Scheme</th>
                                <th onclick="sortData('marks')" id="th-marks">Marks</th>
                                <th onclick="sortData('income')" id="th-income">Annual Income</th>
                                <th onclick="sortData('taluka')" id="th-taluka">Location</th>
                                <th onclick="sortData('status')" id="th-status">Status</th>
                                <th style="cursor: default;">Actions</th>
                            </tr>
                        </thead>
                        <tbody id="table-body">
                            <!-- Populated dynamically -->
                        </tbody>
                    </table>
                </div>

                <!-- Pagination -->
                <div class="pagination-bar">
                    <div class="pagination-info" id="pagination-info">Showing 0 to 0 of 0 entries</div>
                    <div class="pagination-controls" id="pagination-controls">
                        <!-- Populated dynamically -->
                    </div>
                </div>
            </div>
        </div>

        <!-- Audit & Tasks Tab -->
        <div id="audit" class="content-tab">
            <header>
                <div class="page-title">
                    <h2>Tasks & Data Alerts</h2>
                    <p>Address administrative hold-ups, certificate verification checks, and banking discrepancies</p>
                </div>
            </header>

            <div class="audit-layout">
                <!-- Sidebar audit lists -->
                <div class="audit-sidebar">
                    <div class="audit-filter-card active" onclick="switchAuditCategory('all')" id="audit-cat-all">
                        <div class="audit-filter-info">
                            <h4>All Audit Tasks</h4>
                            <p>Everything requiring verification</p>
                        </div>
                        <div class="audit-count info" id="audit-count-all">0</div>
                    </div>

                    <div class="audit-filter-card" onclick="switchAuditCategory('bank_mismatch')" id="audit-cat-bank">
                        <div class="audit-filter-info">
                            <h4>Banking Details Mismatch</h4>
                            <p>Awaiting passbook copy or corrected details</p>
                        </div>
                        <div class="audit-count danger" id="audit-count-bank">0</div>
                    </div>

                    <div class="audit-filter-card" onclick="switchAuditCategory('income_expired')" id="audit-cat-income">
                        <div class="audit-filter-info">
                            <h4>Income Certificate Expired</h4>
                            <p>Require renewal or updated validation</p>
                        </div>
                        <div class="audit-count warning" id="audit-count-income">0</div>
                    </div>

                    <div class="audit-filter-card" onclick="switchAuditCategory('photo_missing')" id="audit-cat-photo">
                        <div class="audit-filter-info">
                            <h4>Missing Identification Photo</h4>
                            <p>Applicants with missing portrait files</p>
                        </div>
                        <div class="audit-count warning" id="audit-count-photo">0</div>
                    </div>

                    <div class="audit-filter-card" onclick="switchAuditCategory('caste_verification')" id="audit-cat-caste">
                        <div class="audit-filter-info">
                            <h4>Caste Verification Pending</h4>
                            <p>Scheduled for community quota verification</p>
                        </div>
                        <div class="audit-count info" id="audit-count-caste">0</div>
                    </div>

                    <div class="audit-filter-card" onclick="switchAuditCategory('duplicate')" id="audit-cat-duplicate">
                        <div class="audit-filter-info">
                            <h4>Duplicate Applications</h4>
                            <p>Needs double-entry merge approval</p>
                        </div>
                        <div class="audit-count danger" id="audit-count-duplicate">0</div>
                    </div>
                </div>

                <!-- Audit List Content -->
                <div class="audit-content" id="audit-list">
                    <!-- Populated dynamically -->
                </div>
            </div>
        </div>

        <!-- Schemes Info Tab -->
        <div id="schemes" class="content-tab">
            <header>
                <div class="page-title">
                    <h2>Scheme Information & Funding</h2>
                    <p>Review budget allocations, eligibility rules, and disbursements per scholarship stream</p>
                </div>
            </header>

            <div class="scheme-grid" id="schemes-grid">
                <!-- Populated dynamically -->
            </div>
        </div>
    </main>

    <!-- Drawer: Profile Details & Administrative Actions -->
    <div class="drawer-overlay" id="drawer-overlay" onclick="closeDrawer()"></div>
    <div class="drawer" id="details-drawer">
        <div class="drawer-header">
            <div class="drawer-title-area">
                <h3 id="d-name">Applicant Name</h3>
                <p>Application ID Reference: #<span id="d-id">000</span></p>
            </div>
            <button class="close-drawer-btn" onclick="closeDrawer()">
                <i class="fa-solid fa-xmark"></i>
            </button>
        </div>

        <div class="drawer-tabs">
            <div class="drawer-tab active" onclick="switchDrawerTab('d-profile', this)">Profile</div>
            <div class="drawer-tab" onclick="switchDrawerTab('d-academic', this)">Academic & School</div>
            <div class="drawer-tab" onclick="switchDrawerTab('d-bank', this)">Banking & Details</div>
            <div class="drawer-tab" onclick="switchDrawerTab('d-remarks', this)">Remarks Log</div>
        </div>

        <div class="drawer-body">
            <!-- Profile Tab -->
            <div id="d-profile" class="drawer-tab-content active">
                <div class="detail-group">
                    <div class="detail-item">
                        <div class="detail-label">Full Name</div>
                        <div class="detail-val" id="d-fullname">-</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Father's Name</div>
                        <div class="detail-val" id="d-father">-</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Birth Year / Age</div>
                        <div class="detail-val" id="d-dob-age">-</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Category</div>
                        <div class="detail-val" id="d-category">-</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Primary Mobile</div>
                        <div class="detail-val" id="d-phone">-</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Alternate Contact</div>
                        <div class="detail-val" id="d-altphone">-</div>
                    </div>
                    <div class="detail-item full-width">
                        <div class="detail-label">Aadhaar Card Number</div>
                        <div class="detail-val" id="d-aadhar">-</div>
                    </div>
                </div>
            </div>

            <!-- Academic Tab -->
            <div id="d-academic" class="drawer-tab-content">
                <div class="detail-group">
                    <div class="detail-item full-width">
                        <div class="detail-label">School / Institution</div>
                        <div class="detail-val" id="d-school">-</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Village / Gaon</div>
                        <div class="detail-val" id="d-village">-</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Taluka</div>
                        <div class="detail-val" id="d-taluka">-</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">District</div>
                        <div class="detail-val" id="d-district">-</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Academic Score</div>
                        <div class="detail-val" id="d-marks">-</div>
                    </div>
                </div>
            </div>

            <!-- Banking Tab -->
            <div id="d-bank" class="drawer-tab-content">
                <div class="detail-group">
                    <div class="detail-item full-width">
                        <div class="detail-label">Bank Account Number</div>
                        <div class="detail-val" id="d-bank-acc">-</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">IFSC Code</div>
                        <div class="detail-val" id="d-ifsc">-</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Status of Bank Details</div>
                        <div class="detail-val" id="d-bank-status">-</div>
                    </div>
                </div>
            </div>

            <!-- Remarks Tab -->
            <div id="d-remarks" class="drawer-tab-content">
                <div class="detail-group">
                    <div class="detail-item full-width">
                        <div class="detail-label">Current Official Remarks</div>
                        <div class="detail-val" id="d-remarks-val" style="padding: 12px; background-color: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; font-style: italic;">-</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Administrative Actions Drawer Box -->
        <div class="drawer-action-box">
            <div class="action-form-row">
                <label class="action-form-label">Review Status</label>
                <select class="action-form-select" id="drawer-action-status">
                    <option value="Pending">Pending</option>
                    <option value="Under Review">Under Review</option>
                    <option value="Approved">Approved</option>
                    <option value="Disbursed">Disbursed</option>
                    <option value="Rejected">Rejected</option>
                </select>
            </div>

            <div class="action-form-row">
                <label class="action-form-label">Update Official Notes / Action Log</label>
                <textarea class="action-form-textarea" id="drawer-action-remarks" placeholder="Enter status update details, missing files requests, or verification comments..."></textarea>
            </div>

            <div class="action-buttons">
                <button class="btn-action-primary" onclick="saveApplicantStatus()">Save Review Updates</button>
                <button class="btn-notify" onclick="simulateNotification()">
                    <i class="fa-solid fa-paper-plane"></i> SMS Alert
                </button>
            </div>
        </div>
    </div>

    <!-- Toast Notifications Container -->
    <div class="toast-container" id="toast-container"></div>

    <!-- Core Javascript Data -->
    <script>
        // Data injected from Python
        let rawApplicants = {json_data};
        
        // App State
        let applicants = [];
        let currentFilters = {{
            search: '',
            status: '',
            scheme: '',
            taluka: '',
            district: '',
            category: ''
        }};
        let currentSort = {{
            key: 'id',
            direction: 'asc'
        }};
        let currentPage = 1;
        const itemsPerPage = 12;
        let selectedApplicantId = null;
        let selectedAuditCategory = 'all';

        // Chart instances
        let statusChartInst = null;
        let schemeChartInst = null;
        let scatterChartInst = null;

        // Scheme Details config
        const schemeDetailsConfig = {{
            "Post-Matric Scholarship Scheme": {{
                desc: "Financial support for post-matriculation studies of student beneficiaries from low income backgrounds.",
                incomeThreshold: 250000,
                baseAmount: 10000
            }},
            "Merit-cum-Means Scholarship": {{
                desc: "Awarded to high academic performers showing excellence under severe financial resource limitations.",
                incomeThreshold: 150000,
                baseAmount: 15000
            }},
            "EBC Scholarship Scheme": {{
                desc: "Educational fee concession support for Economically Backward Class (EBC) beneficiaries.",
                incomeThreshold: 100000,
                baseAmount: 8000
            }},
            "Minority Welfare Scholarship": {{
                desc: "Promotes higher education accessibility for students belonging to notified minority communities.",
                incomeThreshold: 200000,
                baseAmount: 12000
            }},
            "Savitribai Phule Scholarship": {{
                desc: "Fosters education advancement specifically directed to support girl children of marginalized groups.",
                incomeThreshold: 120000,
                baseAmount: 7000
            }},
            "Pre-Matric Scholarship Scheme": {{
                desc: "Aims to help parents of primary-level and secondary-level kids offset education expenses.",
                incomeThreshold: 100000,
                baseAmount: 4000
            }},
            "Rajarshi Shahu Maharaj Scholarship": {{
                desc: "Merit-based assistance for candidates enrolling across recognized degree programs.",
                incomeThreshold: 300000,
                baseAmount: 11000
            }}
        }};

        // LocalStorage keys
        const STORAGE_KEY = 'vidyadaan_applicants_v1';
        const THEME_KEY = 'vidyadaan_theme_v1';

        // Initializer
        window.addEventListener('DOMContentLoaded', () => {{
            loadData();
            initFilters();
            applyFilters();
            renderCharts();
            renderSchemes();
            applyThemeFromStorage();
        }});

        function loadData() {{
            const stored = localStorage.getItem(STORAGE_KEY);
            if (stored) {{
                try {{
                    applicants = JSON.parse(stored);
                }} catch(e) {{
                    applicants = [...rawApplicants];
                }}
            }} else {{
                applicants = [...rawApplicants];
                saveToStorage();
            }}
        }}

        function saveToStorage() {{
            localStorage.setItem(STORAGE_KEY, JSON.stringify(applicants));
        }}

        function resetData() {{
            if (confirm("Are you sure you want to reset all local changes back to the original CSV file data?")) {{
                applicants = JSON.parse(JSON.stringify(rawApplicants));
                saveToStorage();
                applyFilters();
                updateOverviewKPIs();
                updateCharts();
                renderSchemes();
                showToast("System database has been reset to original values.", "info");
            }}
        }}

        // Theme management
        function toggleTheme() {{
            const body = document.body;
            body.classList.toggle('light-theme');
            const isLight = body.classList.contains('light-theme');
            localStorage.setItem(THEME_KEY, isLight ? 'light' : 'dark');
            
            const icon = document.getElementById('theme-icon');
            const text = document.getElementById('theme-text');
            if (isLight) {{
                icon.className = 'fa-solid fa-sun';
                text.textContent = 'Light Mode';
            }} else {{
                icon.className = 'fa-solid fa-moon';
                text.textContent = 'Dark Mode';
            }}

            // Re-render charts for appropriate grid/font colors
            updateCharts();
        }}

        function applyThemeFromStorage() {{
            const theme = localStorage.getItem(THEME_KEY);
            const icon = document.getElementById('theme-icon');
            const text = document.getElementById('theme-text');
            if (theme === 'light') {{
                document.body.classList.add('light-theme');
                icon.className = 'fa-solid fa-sun';
                text.textContent = 'Light Mode';
            }} else {{
                document.body.classList.remove('light-theme');
                icon.className = 'fa-solid fa-moon';
                text.textContent = 'Dark Mode';
            }}
        }}

        // Tab switcher
        function switchTab(tabId, el) {{
            // Navigation items toggle
            document.querySelectorAll('.nav-item').forEach(item => {{
                item.classList.remove('active');
            }});
            el.classList.add('active');

            // Tabs content toggle
            document.querySelectorAll('.content-tab').forEach(tab => {{
                tab.classList.remove('active');
            }});
            document.getElementById(tabId).classList.add('active');

            // Update tab-specific views
            if (tabId === 'overview') {{
                updateOverviewKPIs();
                updateCharts();
            }} else if (tabId === 'audit') {{
                renderAuditSection();
            }} else if (tabId === 'schemes') {{
                renderSchemes();
            }}
        }}

        // Populate filter dropdowns on load
        function initFilters() {{
            const schemes = new Set();
            const talukas = new Set();
            const districts = new Set();
            const categories = new Set();

            applicants.forEach(a => {{
                if (a.scheme) schemes.add(a.scheme);
                if (a.taluka) talukas.add(a.taluka);
                if (a.district) districts.add(a.district);
                if (a.category) categories.add(a.category);
            }});

            populateSelect('filter-scheme', Array.from(schemes).sort());
            populateSelect('filter-taluka', Array.from(talukas).sort());
            populateSelect('filter-district', Array.from(districts).sort());
            populateSelect('filter-category', Array.from(categories).sort());
        }}

        function populateSelect(id, list) {{
            const select = document.getElementById(id);
            // clear dynamic options
            while (select.options.length > 1) {{
                select.remove(1);
            }}
            list.forEach(val => {{
                const opt = document.createElement('option');
                opt.value = val;
                opt.textContent = val;
                select.appendChild(opt);
            }});
        }}

        // Apply filters & render Applications Registry
        function applyFilters() {{
            currentFilters.search = document.getElementById('search-box').value.trim().toLowerCase();
            currentFilters.status = document.getElementById('filter-status').value;
            currentFilters.scheme = document.getElementById('filter-scheme').value;
            currentFilters.taluka = document.getElementById('filter-taluka').value;
            currentFilters.district = document.getElementById('filter-district').value;
            currentFilters.category = document.getElementById('filter-category').value;

            // Perform filtering
            let filtered = applicants.filter(a => {{
                // Search term match
                if (currentFilters.search) {{
                    const s = currentFilters.search;
                    const matchesSearch = 
                        a.name.toLowerCase().includes(s) ||
                        a.father_name.toLowerCase().includes(s) ||
                        a.school.toLowerCase().includes(s) ||
                        a.village.toLowerCase().includes(s) ||
                        a.taluka.toLowerCase().includes(s) ||
                        a.district.toLowerCase().includes(s) ||
                        a.aadhar.toLowerCase().includes(s) ||
                        a.scheme.toLowerCase().includes(s) ||
                        a.remarks.toLowerCase().includes(s);
                    
                    if (!matchesSearch) return false;
                }}

                if (currentFilters.status && a.status !== currentFilters.status) return false;
                if (currentFilters.scheme && a.scheme !== currentFilters.scheme) return false;
                if (currentFilters.taluka && a.taluka !== currentFilters.taluka) return false;
                if (currentFilters.district && a.district !== currentFilters.district) return false;
                if (currentFilters.category && a.category !== currentFilters.category) return false;

                return true;
            }});

            // Sorting
            filtered.sort((a, b) => {{
                let valA = a[currentSort.key];
                let valB = b[currentSort.key];

                if (typeof valA === 'string') {{
                    valA = valA.toLowerCase();
                    valB = valB.toLowerCase();
                }}

                if (valA < valB) return currentSort.direction === 'asc' ? -1 : 1;
                if (valA > valB) return currentSort.direction === 'asc' ? 1 : -1;
                return 0;
            }});

            // Update Active Filter Badges
            renderActiveFilterBadges();

            // Pagination calculations
            const totalItems = filtered.length;
            const totalPages = Math.max(1, Math.ceil(totalItems / itemsPerPage));
            if (currentPage > totalPages) currentPage = totalPages;

            const startIndex = (currentPage - 1) * itemsPerPage;
            const endIndex = Math.min(startIndex + itemsPerPage, totalItems);
            const paginatedItems = filtered.slice(startIndex, endIndex);

            // Render table rows
            const tbody = document.getElementById('table-body');
            tbody.innerHTML = '';

            if (paginatedItems.length === 0) {{
                tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-secondary); padding: 40px;">No applications found matching the selected filters.</td></tr>`;
            }} else {{
                paginatedItems.forEach(a => {{
                    const tr = document.createElement('tr');
                    
                    // Status Badge Class
                    let badgeClass = 'badge-pending';
                    if (a.status === 'Disbursed') badgeClass = 'badge-disbursed';
                    else if (a.status === 'Approved') badgeClass = 'badge-approved';
                    else if (a.status === 'Under Review') badgeClass = 'badge-review';
                    else if (a.status === 'Rejected') badgeClass = 'badge-rejected';

                    tr.innerHTML = `
                        <td style="font-weight: 600; color: var(--text-secondary);">#${{a.id}}</td>
                        <td>
                            <div style="font-weight: 600; color: var(--text-primary);">${{a.name}}</div>
                            <div style="font-size: 0.75rem; color: var(--text-secondary);">${{a.category}} | DOB: ${{a.dob}}</div>
                        </td>
                        <td>
                            <div style="font-weight: 500;">${{a.scheme}}</div>
                            <div style="font-size: 0.75rem; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 250px;">${{a.school}}</div>
                        </td>
                        <td>
                            <div style="font-weight: 700; color: ${{a.marks >= 75 ? 'var(--success-color)' : 'var(--text-primary)'}}">${{a.marks}}%</div>
                        </td>
                        <td>
                            <div style="font-weight: 500;">₹${{a.income.toLocaleString('en-IN')}}</div>
                        </td>
                        <td>
                            <div style="font-weight: 500;">${{a.taluka}}</div>
                            <div style="font-size: 0.75rem; color: var(--text-secondary);">${{a.district}}</div>
                        </td>
                        <td>
                            <span class="badge ${{badgeClass}}">${{a.status}}</span>
                        </td>
                        <td>
                            <button class="btn-view" onclick="openApplicantDetail(${{a.id}})">
                                <i class="fa-regular fa-eye"></i> Details
                            </button>
                        </td>
                    `;
                    tbody.appendChild(tr);
                }});
            }}

            // Update pagination text
            document.getElementById('pagination-info').textContent = 
                totalItems > 0 
                    ? `Showing ${{startIndex + 1}} to ${{endIndex}} of ${{totalItems}} applicants` 
                    : 'Showing 0 to 0 of 0 applicants';

            // Render pagination buttons
            const pControls = document.getElementById('pagination-controls');
            pControls.innerHTML = '';

            const prevBtn = document.createElement('button');
            prevBtn.className = 'page-btn';
            prevBtn.innerHTML = '<i class="fa-solid fa-chevron-left"></i>';
            prevBtn.disabled = currentPage === 1;
            prevBtn.onclick = () => {{ currentPage--; applyFilters(); }};
            pControls.appendChild(prevBtn);

            // Show page numbers
            const maxVisiblePages = 5;
            let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
            let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);

            if (endPage - startPage + 1 < maxVisiblePages) {{
                startPage = Math.max(1, endPage - maxVisiblePages + 1);
            }}

            for (let i = startPage; i <= endPage; i++) {{
                const pageNum = document.createElement('button');
                pageNum.className = `page-btn page-number ${{i === currentPage ? 'active' : ''}}`;
                pageNum.textContent = i;
                pageNum.onclick = () => {{ currentPage = i; applyFilters(); }};
                pControls.appendChild(pageNum);
            }}

            const nextBtn = document.createElement('button');
            nextBtn.className = 'page-btn';
            nextBtn.innerHTML = '<i class="fa-solid fa-chevron-right"></i>';
            nextBtn.disabled = currentPage === totalPages;
            nextBtn.onclick = () => {{ currentPage++; applyFilters(); }};
            pControls.appendChild(nextBtn);

            // Update overview KPIs (even if not visible)
            updateOverviewKPIs();
        }}

        // Render Active Filter Badges
        function renderActiveFilterBadges() {{
            const badgeContainer = document.getElementById('active-filters-list');
            badgeContainer.innerHTML = '';

            const filterKeys = [
                {{ key: 'status', label: 'Status' }},
                {{ key: 'scheme', label: 'Scheme' }},
                {{ key: 'taluka', label: 'Taluka' }},
                {{ key: 'district', label: 'District' }},
                {{ key: 'category', label: 'Category' }}
            ];

            let hasActive = false;

            filterKeys.forEach(f => {{
                if (currentFilters[f.key]) {{
                    hasActive = true;
                    const badge = document.createElement('div');
                    badge.className = 'active-filter-badge';
                    badge.innerHTML = `
                        ${{f.label}}: ${{currentFilters[f.key]}}
                        <i class="fa-solid fa-circle-xmark" onclick="removeFilter('${{f.key}}')"></i>
                    `;
                    badgeContainer.appendChild(badge);
                }}
            }});

            if (hasActive) {{
                badgeContainer.style.margin = '8px 0 0 0';
            }} else {{
                badgeContainer.style.margin = '0';
            }}
        }}

        function removeFilter(key) {{
            document.getElementById('filter-' + key).value = '';
            applyFilters();
        }}

        function clearFilters() {{
            document.getElementById('search-box').value = '';
            document.getElementById('filter-status').value = '';
            document.getElementById('filter-scheme').value = '';
            document.getElementById('filter-taluka').value = '';
            document.getElementById('filter-district').value = '';
            document.getElementById('filter-category').value = '';
            applyFilters();
            showToast("All filters cleared.", "info");
        }}

        // Sorting Logic
        function sortData(key) {{
            if (currentSort.key === key) {{
                currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
            }} else {{
                currentSort.key = key;
                currentSort.direction = 'asc';
            }}

            // Update header class indicators
            document.querySelectorAll('th').forEach(th => {{
                th.classList.remove('sorted-asc', 'sorted-desc');
            }});

            const sortedTh = document.getElementById('th-' + key);
            if (sortedTh) {{
                sortedTh.classList.add(currentSort.direction === 'asc' ? 'sorted-asc' : 'sorted-desc');
            }}

            applyFilters();
        }}

        // Overview KPI computation
        function updateOverviewKPIs() {{
            const totalApps = applicants.length;
            
            let disbursedAmt = 0;
            let disbursedCount = 0;
            let approvedAmt = 0;
            let approvedCount = 0;
            let reviewCount = 0;
            let pendingCount = 0;
            let rejectedCount = 0;
            let totalMarks = 0;
            let totalIncome = 0;

            applicants.forEach(a => {{
                totalMarks += a.marks;
                totalIncome += a.income;

                if (a.status === 'Disbursed') {{
                    disbursedAmt += a.amount;
                    disbursedCount++;
                }} else if (a.status === 'Approved') {{
                    approvedAmt += a.amount;
                    approvedCount++;
                }} else if (a.status === 'Under Review') {{
                    reviewCount++;
                }} else if (a.status === 'Pending') {{
                    pendingCount++;
                }} else if (a.status === 'Rejected') {{
                    rejectedCount++;
                }}
            }});

            const avgMarks = totalApps > 0 ? (totalMarks / totalApps).toFixed(1) : 0;
            const avgIncome = totalApps > 0 ? Math.round(totalIncome / totalApps) : 0;

            // DOM Updates
            document.getElementById('kpi-total-apps').textContent = totalApps;
            document.getElementById('kpi-disbursed-amount').textContent = '₹' + disbursedAmt.toLocaleString('en-IN');
            document.getElementById('kpi-disbursed-count').textContent = `${{disbursedCount}} Disbursed Applications`;
            document.getElementById('kpi-approved-amount').textContent = '₹' + approvedAmt.toLocaleString('en-IN');
            document.getElementById('kpi-approved-count').textContent = `${{approvedCount}} Approved (Awaiting Fund)`;
            document.getElementById('kpi-review-count').textContent = reviewCount + pendingCount;
            document.getElementById('kpi-pending-sub').textContent = `${{reviewCount}} in Review | ${{pendingCount}} Pending Verification`;
            document.getElementById('kpi-avg-marks').textContent = avgMarks + '%';
            document.getElementById('kpi-avg-income').textContent = '₹' + avgIncome.toLocaleString('en-IN');
        }}

        // Drawer functionality
        function openApplicantDetail(id) {{
            const a = applicants.find(x => x.id === id);
            if (!a) return;

            selectedApplicantId = id;

            // Header info
            document.getElementById('d-name').textContent = a.name;
            document.getElementById('d-id').textContent = String(a.id).padStart(3, '0');

            // Profile Tab
            document.getElementById('d-fullname').textContent = a.name;
            document.getElementById('d-father').textContent = a.father_name;
            document.getElementById('d-dob-age').textContent = `${{a.dob}} / ${{a.age}} Years`;
            document.getElementById('d-category').textContent = a.category;
            document.getElementById('d-phone').textContent = a.phone;
            document.getElementById('d-altphone').textContent = a.alt_phone || 'None';
            document.getElementById('d-aadhar').textContent = a.aadhar;

            // Academic Tab
            document.getElementById('d-school').textContent = a.school;
            document.getElementById('d-village').textContent = a.village;
            document.getElementById('d-taluka').textContent = a.taluka;
            document.getElementById('d-district').textContent = a.district;
            document.getElementById('d-marks').textContent = a.marks + '%';

            // Bank Details
            document.getElementById('d-bank-acc').textContent = a.bank_account;
            document.getElementById('d-ifsc').textContent = a.ifsc;
            
            // Check bank issue status
            const isBankIssue = a.remarks.toLowerCase().includes('bank') || a.remarks.toLowerCase().includes('account') || a.remarks.toLowerCase().includes('passbook');
            const bankStatusEl = document.getElementById('d-bank-status');
            if (isBankIssue) {{
                bankStatusEl.innerHTML = `<span style="color: var(--danger-color); font-weight: 600;"><i class="fa-solid fa-circle-exclamation"></i> Discrepancy Found (Remarks mismatch)</span>`;
            }} else {{
                bankStatusEl.innerHTML = `<span style="color: var(--success-color); font-weight: 600;"><i class="fa-solid fa-circle-check"></i> Standard Details Validated</span>`;
            }}

            // Remarks
            document.getElementById('d-remarks-val').textContent = a.remarks || 'No official notes added.';

            // Inputs in action box
            document.getElementById('drawer-action-status').value = a.status;
            document.getElementById('drawer-action-remarks').value = a.remarks;

            // Switch to Profile Tab by default inside drawer
            document.querySelectorAll('.drawer-tab').forEach((tab, index) => {{
                tab.classList.remove('active');
                if (index === 0) tab.classList.add('active');
            }});
            document.querySelectorAll('.drawer-tab-content').forEach((content, index) => {{
                content.classList.remove('active');
                if (index === 0) content.classList.add('active');
            }});

            // Show drawer
            document.getElementById('drawer-overlay').classList.add('open');
            document.getElementById('details-drawer').classList.add('open');
        }}

        function closeDrawer() {{
            document.getElementById('drawer-overlay').classList.remove('open');
            document.getElementById('details-drawer').classList.remove('open');
            selectedApplicantId = null;
        }}

        function switchDrawerTab(tabId, el) {{
            document.querySelectorAll('.drawer-tab').forEach(tab => {{
                tab.classList.remove('active');
            }});
            el.classList.add('active');

            document.querySelectorAll('.drawer-tab-content').forEach(content => {{
                content.classList.remove('active');
            }});
            document.getElementById(tabId).classList.add('active');
        }}

        // Save Review updates inside Drawer
        function saveApplicantStatus() {{
            if (!selectedApplicantId) return;

            const a = applicants.find(x => x.id === selectedApplicantId);
            if (!a) return;

            const oldStatus = a.status;
            const newStatus = document.getElementById('drawer-action-status').value;
            const newRemarks = document.getElementById('drawer-action-remarks').value.trim();

            a.status = newStatus;
            a.remarks = newRemarks;

            saveToStorage();
            applyFilters();
            
            // If in audit tab, re-render audit section
            if (document.getElementById('audit').classList.contains('active')) {{
                renderAuditSection();
            }}

            closeDrawer();
            showToast(`Application #${{a.id}} updated from '${{oldStatus}}' to '${{newStatus}}' successfully!`, "success");
        }}

        function simulateNotification() {{
            if (!selectedApplicantId) return;
            const a = applicants.find(x => x.id === selectedApplicantId);
            if (!a) return;

            showToast(`SMS alert dispatched to applicant phone ${{a.phone}} with details: "Status updated to ${{a.status}}."`, "success");
        }}

        // Toast notifications logic
        function showToast(message, type = 'success') {{
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            toast.className = `toast ${{type}}`;
            
            let icon = 'fa-circle-check';
            if (type === 'warning') icon = 'fa-triangle-exclamation';
            else if (type === 'danger') icon = 'fa-circle-xmark';
            else if (type === 'info') icon = 'fa-circle-info';

            toast.innerHTML = `
                <i class="fa-solid ${{icon}}"></i>
                <div style="font-size: 0.85rem; font-weight: 500;">${{message}}</div>
            `;
            
            container.appendChild(toast);

            setTimeout(() => {{
                toast.style.opacity = '0';
                toast.style.transform = 'translateY(-10px)';
                toast.style.transition = 'all 0.3s';
                setTimeout(() => {{
                    toast.remove();
                }}, 300);
            }}, 4000);
        }}

        // Charts configuration
        function getChartColors() {{
            const isLight = document.body.classList.contains('light-theme');
            return {{
                text: isLight ? '#0f172a' : '#f8fafc',
                textMuted: isLight ? '#64748b' : '#94a3b8',
                grid: isLight ? '#cbd5e1' : '#334155',
                cardBg: isLight ? '#ffffff' : '#1e293b'
            }};
        }}

        function renderCharts() {{
            const colors = getChartColors();
            Chart.defaults.color = colors.textMuted;
            Chart.defaults.font.family = "'Inter', sans-serif";

            // Status Chart (Doughnut)
            const ctxStatus = document.getElementById('statusChart').getContext('2d');
            const statusCounts = {{ 'Disbursed': 0, 'Approved': 0, 'Under Review': 0, 'Pending': 0, 'Rejected': 0 }};
            applicants.forEach(a => {{ if (statusCounts.hasOwnProperty(a.status)) statusCounts[a.status]++; }});

            statusChartInst = new Chart(ctxStatus, {{
                type: 'doughnut',
                data: {{
                    labels: Object.keys(statusCounts),
                    datasets: [{{
                        data: Object.values(statusCounts),
                        backgroundColor: [
                            '#10b981', // Disbursed (success)
                            '#3b82f6', // Approved (info)
                            '#f59e0b', // Under Review (warning)
                            '#8b5cf6', // Pending (purple)
                            '#ef4444'  // Rejected (danger)
                        ],
                        borderWidth: 0,
                        hoverOffset: 4
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            position: 'right',
                            labels: {{
                                color: colors.text,
                                boxWidth: 12,
                                padding: 15
                            }}
                        }}
                    }},
                    cutout: '70%'
                }}
            }});

            // Scheme Chart (Bar)
            const ctxScheme = document.getElementById('schemeChart').getContext('2d');
            const schemeCounts = {{}};
            applicants.forEach(a => {{
                schemeCounts[a.scheme] = (schemeCounts[a.scheme] || 0) + 1;
            }});

            schemeChartInst = new Chart(ctxScheme, {{
                type: 'bar',
                data: {{
                    labels: Object.keys(schemeCounts).map(s => s.replace(" Scholarship", "").replace(" Scheme", "")),
                    datasets: [{{
                        label: 'Applications',
                        data: Object.values(schemeCounts),
                        backgroundColor: '#6366f1',
                        borderRadius: 6,
                        barThickness: 20
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{ display: false }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            grid: {{ color: colors.grid }},
                            ticks: {{ color: colors.textMuted }}
                        }},
                        x: {{
                            grid: {{ display: false }},
                            ticks: {{ color: colors.textMuted }}
                        }}
                    }}
                }}
            }});

            // Scatter Plot: Marks % vs Family Income
            const ctxScatter = document.getElementById('scatterChart').getContext('2d');
            
            const getScatterData = () => {{
                const statusColors = {{
                    'Disbursed': '#10b981',
                    'Approved': '#3b82f6',
                    'Under Review': '#f59e0b',
                    'Pending': '#8b5cf6',
                    'Rejected': '#ef4444'
                }};

                // Map applicants to datasets grouped by status
                const groups = {{}};
                applicants.forEach(a => {{
                    if (!groups[a.status]) {{
                        groups[a.status] = [];
                    }}
                    groups[a.status].push({{
                        x: a.income,
                        y: a.marks,
                        name: a.name,
                        school: a.school,
                        scheme: a.scheme
                    }});
                }});

                return Object.keys(groups).map(status => ({{
                    label: status,
                    data: groups[status],
                    backgroundColor: statusColors[status] || '#94a3b8',
                    pointRadius: 6,
                    pointHoverRadius: 8
                }}));
            }};

            scatterChartInst = new Chart(ctxScatter, {{
                type: 'scatter',
                data: {{
                    datasets: getScatterData()
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            position: 'top',
                            labels: {{
                                color: colors.text,
                                boxWidth: 10
                            }}
                        }},
                        tooltip: {{
                            callbacks: {{
                                label: function(ctx) {{
                                    const pt = ctx.raw;
                                    return [
                                        `Name: ${{pt.name}}`,
                                        `Income: ₹${{pt.x.toLocaleString('en-IN')}}`,
                                        `Marks: ${{pt.y}}%`,
                                        `Scheme: ${{pt.scheme}}`
                                    ];
                                }}
                            }}
                        }}
                    }},
                    scales: {{
                        x: {{
                            title: {{
                                display: true,
                                text: 'Annual Family Income (INR)',
                                color: colors.text
                            }},
                            grid: {{ color: colors.grid }},
                            ticks: {{
                                color: colors.textMuted,
                                callback: function(value) {{
                                    return '₹' + (value/1000) + 'k';
                                }}
                            }}
                        }},
                        y: {{
                            title: {{
                                display: true,
                                text: 'Academic Marks (%)',
                                color: colors.text
                            }},
                            grid: {{ color: colors.grid }},
                            ticks: {{ color: colors.textMuted }}
                        }}
                    }}
                }}
            }});
        }}

        function updateCharts() {{
            if (!statusChartInst || !schemeChartInst || !scatterChartInst) return;

            const colors = getChartColors();
            Chart.defaults.color = colors.textMuted;

            // Update status chart
            const statusCounts = {{ 'Disbursed': 0, 'Approved': 0, 'Under Review': 0, 'Pending': 0, 'Rejected': 0 }};
            applicants.forEach(a => {{ if (statusCounts.hasOwnProperty(a.status)) statusCounts[a.status]++; }});
            statusChartInst.data.datasets[0].data = Object.values(statusCounts);
            statusChartInst.options.plugins.legend.labels.color = colors.text;
            statusChartInst.update();

            // Update scheme chart
            const schemeCounts = {{}};
            applicants.forEach(a => {{ schemeCounts[a.scheme] = (schemeCounts[a.scheme] || 0) + 1; }});
            schemeChartInst.data.datasets[0].data = Object.values(schemeCounts);
            schemeChartInst.options.scales.y.grid.color = colors.grid;
            schemeChartInst.options.scales.y.ticks.color = colors.textMuted;
            schemeChartInst.options.scales.x.ticks.color = colors.textMuted;
            schemeChartInst.update();

            // Update scatter chart
            const statusColors = {{
                'Disbursed': '#10b981',
                'Approved': '#3b82f6',
                'Under Review': '#f59e0b',
                'Pending': '#8b5cf6',
                'Rejected': '#ef4444'
            }};
            const groups = {{}};
            applicants.forEach(a => {{
                if (!groups[a.status]) groups[a.status] = [];
                groups[a.status].push({{
                    x: a.income,
                    y: a.marks,
                    name: a.name,
                    school: a.school,
                    scheme: a.scheme
                }});
            }});

            const newDatasets = Object.keys(groups).map(status => ({{
                label: status,
                data: groups[status],
                backgroundColor: statusColors[status] || '#94a3b8',
                pointRadius: 6,
                pointHoverRadius: 8
            }}));

            scatterChartInst.data.datasets = newDatasets;
            scatterChartInst.options.plugins.legend.labels.color = colors.text;
            scatterChartInst.options.scales.x.title.color = colors.text;
            scatterChartInst.options.scales.x.grid.color = colors.grid;
            scatterChartInst.options.scales.x.ticks.color = colors.textMuted;
            scatterChartInst.options.scales.y.title.color = colors.text;
            scatterChartInst.options.scales.y.grid.color = colors.grid;
            scatterChartInst.options.scales.y.ticks.color = colors.textMuted;
            scatterChartInst.update();
        }}

        // Audit & alerts logic
        function checkApplicantAuditIssue(a, category) {{
            const remarksLower = a.remarks.toLowerCase();
            const hasBankIssue = remarksLower.includes('bank') || remarksLower.includes('account') || remarksLower.includes('passbook');
            const hasIncomeIssue = remarksLower.includes('income') || remarksLower.includes('expired');
            const hasPhotoIssue = remarksLower.includes('photo') || remarksLower.includes('missing');
            const hasCasteIssue = remarksLower.includes('caste') || remarksLower.includes('caste certificate');
            const hasDuplicateIssue = remarksLower.includes('duplicate') || remarksLower.includes('merged');

            if (category === 'all') {{
                return (hasBankIssue || hasIncomeIssue || hasPhotoIssue || hasCasteIssue || hasDuplicateIssue);
            }}
            if (category === 'bank_mismatch') return hasBankIssue;
            if (category === 'income_expired') return hasIncomeIssue;
            if (category === 'photo_missing') return hasPhotoIssue;
            if (category === 'caste_verification') return hasCasteIssue;
            if (category === 'duplicate') return hasDuplicateIssue;
            
            return false;
        }}

        function switchAuditCategory(cat) {{
            document.querySelectorAll('.audit-filter-card').forEach(card => {{
                card.classList.remove('active');
            }});
            
            let cardId = 'audit-cat-all';
            if (cat === 'bank_mismatch') cardId = 'audit-cat-bank';
            else if (cat === 'income_expired') cardId = 'audit-cat-income';
            else if (cat === 'photo_missing') cardId = 'audit-cat-photo';
            else if (cat === 'caste_verification') cardId = 'audit-cat-caste';
            else if (cat === 'duplicate') cardId = 'audit-cat-duplicate';

            document.getElementById(cardId).classList.add('active');
            selectedAuditCategory = cat;
            renderAuditSection();
        }}

        function renderAuditSection() {{
            const listEl = document.getElementById('audit-list');
            listEl.innerHTML = '';

            // Compute counts for audit sidebar
            let allCount = 0;
            let bankCount = 0;
            let incomeCount = 0;
            let photoCount = 0;
            let casteCount = 0;
            let duplicateCount = 0;

            applicants.forEach(a => {{
                if (checkApplicantAuditIssue(a, 'all')) allCount++;
                if (checkApplicantAuditIssue(a, 'bank_mismatch')) bankCount++;
                if (checkApplicantAuditIssue(a, 'income_expired')) incomeCount++;
                if (checkApplicantAuditIssue(a, 'photo_missing')) photoCount++;
                if (checkApplicantAuditIssue(a, 'caste_verification')) casteCount++;
                if (checkApplicantAuditIssue(a, 'duplicate')) duplicateCount++;
            }});

            document.getElementById('audit-count-all').textContent = allCount;
            document.getElementById('audit-count-bank').textContent = bankCount;
            document.getElementById('audit-count-income').textContent = incomeCount;
            document.getElementById('audit-count-photo').textContent = photoCount;
            document.getElementById('audit-count-caste').textContent = casteCount;
            document.getElementById('audit-count-duplicate').textContent = duplicateCount;

            // Filter applicants for the selected category
            const filtered = applicants.filter(a => checkApplicantAuditIssue(a, selectedAuditCategory));

            if (filtered.length === 0) {{
                listEl.innerHTML = `
                    <div style="background-color: var(--bg-secondary); border: 1px dashed var(--border-color); border-radius: 12px; padding: 60px; text-align: center; color: var(--text-secondary);">
                        <i class="fa-regular fa-circle-check" style="font-size: 3rem; color: var(--success-color); margin-bottom: 16px;"></i>
                        <h3>All Clean!</h3>
                        <p style="margin-top: 8px;">No outstanding administrative tasks or alerts found for this category.</p>
                    </div>
                `;
                return;
            }}

            filtered.forEach(a => {{
                const card = document.createElement('div');
                card.className = 'audit-card';

                // Categorize issue for local display badge
                let issueName = 'General Verification';
                let badgeStyle = 'background-color: var(--info-glow); color: var(--info-color);';
                
                if (checkApplicantAuditIssue(a, 'bank_mismatch')) {{
                    issueName = 'Bank Detail Discrepancy';
                    badgeStyle = 'background-color: var(--danger-glow); color: var(--danger-color);';
                }} else if (checkApplicantAuditIssue(a, 'income_expired')) {{
                    issueName = 'Income Certificate Expired';
                    badgeStyle = 'background-color: var(--warning-glow); color: var(--warning-color);';
                }} else if (checkApplicantAuditIssue(a, 'photo_missing')) {{
                    issueName = 'Missing Identification';
                    badgeStyle = 'background-color: var(--warning-glow); color: var(--warning-color);';
                }} else if (checkApplicantAuditIssue(a, 'caste_verification')) {{
                    issueName = 'Caste verification';
                    badgeStyle = 'background-color: var(--primary-glow); color: var(--primary-color);';
                }} else if (checkApplicantAuditIssue(a, 'duplicate')) {{
                    issueName = 'Duplicate Entry Warning';
                    badgeStyle = 'background-color: var(--danger-glow); color: var(--danger-color);';
                }}

                card.innerHTML = `
                    <div class="audit-card-header">
                        <div class="audit-card-title">
                            <span style="font-weight: 700;">${{a.name}}</span>
                            <span style="font-size: 0.8rem; color: var(--text-secondary);">#${{a.id}}</span>
                        </div>
                        <span class="audit-badge" style="${{badgeStyle}}">${{issueName}}</span>
                    </div>
                    <div class="audit-desc">
                        <div><strong>Scheme:</strong> ${{a.scheme}}</div>
                        <div style="margin-top: 4px;"><strong>School:</strong> ${{a.school}} | <strong>Taluka:</strong> ${{a.taluka}}</div>
                        <div style="margin-top: 8px; padding: 10px; background-color: var(--bg-primary); border-radius: 6px; font-style: italic; border: 1px solid var(--border-color);">
                            <i class="fa-solid fa-clipboard-question" style="color: var(--text-secondary); margin-right: 6px;"></i>"${{a.remarks}}"
                        </div>
                    </div>
                    <div class="audit-actions">
                        <button class="btn-view" onclick="openApplicantDetail(${{a.id}})">
                            <i class="fa-solid fa-user-gear"></i> Administrative Action
                        </button>
                    </div>
                `;
                listEl.appendChild(card);
            }});
        }}

        // Render Schemes Details tab
        function renderSchemes() {{
            const grid = document.getElementById('schemes-grid');
            grid.innerHTML = '';

            // Compute counts and disbursed per scheme
            const schemeStats = {{}};
            Object.keys(schemeDetailsConfig).forEach(s => {{
                schemeStats[s] = {{
                    total: 0,
                    disbursed: 0,
                    pending: 0,
                    marksSum: 0
                }};
            }});

            applicants.forEach(a => {{
                if (schemeStats[a.scheme]) {{
                    schemeStats[a.scheme].total++;
                    if (a.status === 'Disbursed') {{
                        schemeStats[a.scheme].disbursed++;
                    }} else if (a.status !== 'Rejected') {{
                        schemeStats[a.scheme].pending++;
                    }}
                    schemeStats[a.scheme].marksSum += a.marks;
                }}
            }});

            Object.keys(schemeDetailsConfig).forEach(scheme => {{
                const cfg = schemeDetailsConfig[scheme];
                const stats = schemeStats[scheme] || {{ total: 0, disbursed: 0, pending: 0, marksSum: 0 }};
                
                const avgMarks = stats.total > 0 ? (stats.marksSum / stats.total).toFixed(1) : '0.0';
                const totalFundDisbursed = stats.disbursed * cfg.baseAmount;

                const card = document.createElement('div');
                card.className = 'scheme-card';

                card.innerHTML = `
                    <div class="scheme-header">
                        <div class="scheme-title">${{scheme}}</div>
                        <div style="font-size: 0.8rem; color: var(--text-secondary); line-height: 1.4; min-height: 50px;">
                            ${{cfg.desc}}
                        </div>
                    </div>
                    <div class="scheme-meta">
                        <div>Income Ceiling: <strong>Max ₹${{cfg.incomeThreshold.toLocaleString('en-IN')}}</strong></div>
                        <div>Base Allocation: <strong>₹${{cfg.baseAmount.toLocaleString('en-IN')}}</strong></div>
                    </div>
                    <div class="scheme-body">
                        <div class="scheme-stat-row">
                            <span class="scheme-stat-label">Total Applications</span>
                            <span class="scheme-stat-val">${{stats.total}}</span>
                        </div>
                        <div class="scheme-stat-row">
                            <span class="scheme-stat-label">Disbursed / Approved</span>
                            <span class="scheme-stat-val" style="color: var(--success-color);">${{stats.disbursed}} / ${{stats.pending}}</span>
                        </div>
                        <div class="scheme-stat-row">
                            <span class="scheme-stat-label">Average Marks</span>
                            <span class="scheme-stat-val">${{avgMarks}}%</span>
                        </div>
                    </div>
                    <div class="scheme-footer-fund">
                        <span class="scheme-fund-label">Total Funds Disbursed</span>
                        <span class="scheme-fund-val">₹${{totalFundDisbursed.toLocaleString('en-IN')}}</span>
                    </div>
                `;
                grid.appendChild(card);
            }});
        }}
    </script>
</body>
</html>
"""

    # Write HTML
    output_path = '/home/desinotorious/src/github.com/bprashanth/io/benchmarks/pii/corpus/dashboard.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"Success! Dashboard compiled successfully to: {output_path}")

if __name__ == '__main__':
    build()
