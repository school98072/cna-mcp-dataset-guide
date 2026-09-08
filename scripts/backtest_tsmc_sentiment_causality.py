import yfinance as yf
import pandas as pd
import numpy as np

def run_backtest():
    print("================================================================================")
    print("  台積電 (2330.TW) 消息面因果定律量化回測與前後窗口交叉驗證")
    print("================================================================================")

    # 1. 下載數據
    print("\n[Step 1] 獲取歷史價格數據...")
    tsmc = yf.download('2330.TW', start='2008-01-01', end='2024-12-31', progress=False)
    twii = yf.download('^TWII', start='2008-01-01', end='2024-12-31', progress=False)
    xinyun = yf.download('3583.TW', start='2024-01-01', end='2024-08-31', progress=False)
    hongsu = yf.download('3131.TWO', start='2024-01-01', end='2024-08-31', progress=False)

    # 處理 multi-index columns if any
    if isinstance(tsmc.columns, pd.MultiIndex):
        tsmc.columns = tsmc.columns.get_level_values(0)
    if isinstance(twii.columns, pd.MultiIndex):
        twii.columns = twii.columns.get_level_values(0)
    if isinstance(xinyun.columns, pd.MultiIndex):
        xinyun.columns = xinyun.columns.get_level_values(0)
    if isinstance(hongsu.columns, pd.MultiIndex):
        hongsu.columns = hongsu.columns.get_level_values(0)

    tsmc['Daily_Return'] = tsmc['Close'].pct_change()
    twii['Daily_Return'] = twii['Close'].pct_change()

    # ==============================================================================
    # 定律一：「買在預期、賣在事實」（Buy the Rumor, Sell the News）
    # ==============================================================================
    print("\n--------------------------------------------------------------------------------")
    print("【定律一驗證】「買在預期、賣在事實」前後窗口報酬率對比")
    print("--------------------------------------------------------------------------------")

    def analyze_event_window(df, event_date_str, label, pre_days=15, post_days=15):
        event_dt = pd.to_datetime(event_date_str)
        # 找到最近的交易日
        trading_days = df.index
        # 確保 timezone 一致
        if trading_days.tz is not None and event_dt.tz is None:
            event_dt = event_dt.tz_localize(trading_days.tz)
            
        locs = np.where(trading_days >= event_dt)[0]
        if len(locs) == 0:
            return
        t0_idx = locs[0]
        t0_date = trading_days[t0_idx]

        # 窗口切片
        pre_idx = max(0, t0_idx - pre_days)
        post_idx = min(len(df) - 1, t0_idx + post_days)

        p_pre_start = df['Close'].iloc[pre_idx]
        p_t0 = df['Close'].iloc[t0_idx]
        p_post_end = df['Close'].iloc[post_idx]

        # 期間最高最低
        pre_max = df['Close'].iloc[pre_idx:t0_idx+1].max()
        post_min = df['Close'].iloc[t0_idx:post_idx+1].min()

        pre_return = (p_t0 - p_pre_start) / p_pre_start * 100
        post_return = (p_post_end - p_t0) / p_t0 * 100
        post_max_drawdown = (post_min - p_t0) / p_t0 * 100

        print(f"▶ 事件: {label} (基準日 T0 = {t0_date.strftime('%Y-%m-%d')})")
        print(f"  • 基準日收盤價: NT$ {p_t0:.2f}")
        print(f"  • 前窗口 [-{pre_days}日] 價格: NT$ {p_pre_start:.2f} ➔ 搶跑漲幅 (Rumor Run-up): {pre_return:+.2f}%")
        print(f"  • 後窗口 [+{post_days}日] 價格: NT$ {p_post_end:.2f} ➔ 事後反應 (Sell-the-News): {post_return:+.2f}%")
        print(f"  • 後窗口最大回撤 (Max Drawdown from T0): {post_max_drawdown:.2f}%\n")
        return {
            'label': label,
            't0_date': t0_date.strftime('%Y-%m-%d'),
            'p_t0': p_t0,
            'pre_return': pre_return,
            'post_return': post_return,
            'post_drawdown': post_max_drawdown
        }

    events = [
        ('2024-07-04', '2024 突破千元 (1005元) 搶跑法說會', 15, 15),
        ('2024-07-18', '2024 Q2 法說會 (優於預期但迎來歷史性暴跌)', 10, 15),
        ('2021-01-14', '2021 Q4 法說會 (宣布280億美元天文資本支出)', 15, 15),
        ('2020-11-17', '2020 首次突破500元心理大關', 15, 15),
        ('2009-06-11', '2009 張忠謀宣布回任總執行長', 15, 15)
    ]

    results_law1 = []
    for dt_str, lbl, pre_d, post_d in events:
        res = analyze_event_window(tsmc, dt_str, lbl, pre_d, post_d)
        if res: results_law1.append(res)

    # ==============================================================================
    # 定律二：「吸金黑洞」到「萬物噴出」的非線性切換
    # ==============================================================================
    print("--------------------------------------------------------------------------------")
    print("【定律二驗證】「吸金黑洞」到「萬物噴出」Beta 擴散實測 (2024 案例)")
    print("--------------------------------------------------------------------------------")

    # 階段 1：吸金黑洞期 (2024-01-02 ~ 2024-03-31)
    # 台積電大漲，帶動大盤，但資金排擠效應明顯
    p1_start = '2024-01-02'
    p1_end = '2024-03-29'
    
    # 階段 2：萬物噴出期 (2024-04-01 ~ 2024-07-15)
    # 台積電破800~1000元，CoWoS 設備股暴衝
    p2_start = '2024-04-01'
    p2_end = '2024-07-11'

    def get_period_returns(df_dict, start_d, end_d):
        out = {}
        for name, d in df_dict.items():
            sub = d.loc[start_d:end_d]
            if len(sub) > 0:
                ret = (sub['Close'].iloc[-1] - sub['Close'].iloc[0]) / sub['Close'].iloc[0] * 100
                out[name] = ret
        return out

    stocks_2024 = {
        '台積電 (2330.TW)': tsmc,
        '加權指數 (^TWII)': twii,
        '辛耘 CoWoS設備 (3583.TW)': xinyun,
        '弘塑 CoWoS設備 (3131.TWO)': hongsu
    }

    ret_p1 = get_period_returns(stocks_2024, p1_start, p1_end)
    ret_p2 = get_period_returns(stocks_2024, p2_start, p2_end)

    print("▶ 階段一：吸金黑洞期 (2024-01-02 至 2024-03-29)")
    for k, v in ret_p1.items():
        print(f"  • {k}: {v:+.2f}%")

    print("\n▶ 階段二：萬物噴出期 (2024-04-01 至 2024-07-11，台積破千前後)")
    for k, v in ret_p2.items():
        print(f"  • {k}: {v:+.2f}%")

    # ==============================================================================
    # 定律三：交易微結構突變（千元檔位跳動加劇波動）
    # ==============================================================================
    print("\n--------------------------------------------------------------------------------")
    print("【定律三驗證】千元檔位跳動（每跳1元 ➔ 每跳5元）市場波動率實測")
    print("--------------------------------------------------------------------------------")

    # 期間 A: 千元之前 (2024-01-02 ~ 2024-06-30，跳動 1 元)
    # 期間 B: 千元之後 (2024-07-04 ~ 2024-08-31，跳動 5 元)
    sub_pre = tsmc.loc['2024-01-02':'2024-06-30']
    sub_post = tsmc.loc['2024-07-04':'2024-08-30']

    twii_pre = twii.loc['2024-01-02':'2024-06-30']
    twii_post = twii.loc['2024-07-04':'2024-08-30']

    # 1. 日內高低振幅百分比 (High - Low) / Close
    tsmc_range_pre = ((sub_pre['High'] - sub_pre['Low']) / sub_pre['Close'] * 100).mean()
    tsmc_range_post = ((sub_post['High'] - sub_post['Low']) / sub_post['Close'] * 100).mean()

    twii_range_pre = ((twii_pre['High'] - twii_pre['Low']) / twii_pre['Close'] * 100).mean()
    twii_range_post = ((twii_post['High'] - twii_post['Low']) / twii_post['Close'] * 100).mean()

    # 2. 年化歷史實現波動率 Realized Volatility
    tsmc_vol_pre = sub_pre['Daily_Return'].std() * np.sqrt(252) * 100
    tsmc_vol_post = sub_post['Daily_Return'].std() * np.sqrt(252) * 100

    twii_vol_pre = twii_pre['Daily_Return'].std() * np.sqrt(252) * 100
    twii_vol_post = twii_post['Daily_Return'].std() * np.sqrt(252) * 100

    print("▶ 1. 日內平均振幅 [(High - Low) / Close %]:")
    print(f"  • 台積電 (千元前 1元/檔): {tsmc_range_pre:.2f}%  ➔  (千元後 5元/檔): {tsmc_range_post:.2f}%  (波動擴大 {tsmc_range_post/tsmc_range_pre:.2f} 倍)")
    print(f"  • 大盤指數 (^TWII):       {twii_range_pre:.2f}%  ➔  (千元後 5元/檔): {twii_range_post:.2f}%  (波動擴大 {twii_range_post/twii_range_pre:.2f} 倍)")

    print("\n▶ 2. 年化實現波動率 (Realized Volatility %):")
    print(f"  • 台積電 (千元前): {tsmc_vol_pre:.2f}%  ➔  (千元後): {tsmc_vol_post:.2f}%  (年化波動飆升 {tsmc_vol_post - tsmc_vol_pre:+.2f} 個百分點)")
    print(f"  • 大盤指數 (^TWII): {twii_vol_pre:.2f}%  ➔  (千元後): {twii_vol_post:.2f}%  (年化波動飆升 {twii_vol_post - twii_vol_pre:+.2f} 個百分點)")

    print("\n================================================================================")
    print("  量化回測完畢，所有數據來自台灣證券交易所歷史真實成交行情！")
    print("================================================================================")

if __name__ == '__main__':
    run_backtest()
