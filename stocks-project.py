# ----------------------------------- #
# LIBRARIES 
# ----------------------------------- #
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
from bs4 import BeautifulSoup

st.set_page_config(page_title="BIST Hisse Senedi Görüntüleyici", layout="wide", page_icon="📈")
st.title("📈 BIST Hisse Senedi Görüntüleyici")

@st.cache_data(ttl=7*24*3600) # Haftada bir kez güncelle (çok sık değişmediği için)
def get_all_bist_tickers():
    bist_list = []
    
    # 1. YÖNTEM: İş Yatırım üzerinden güncel hisseleri çekmeyi dene 
    # (KAP ve Wikipedia bazen Streamlit sunucularını engelleyebiliyor)
    try:
        import requests
        from io import StringIO
        import pandas as pd
        url = "https://www.isyatirim.com.tr/tr-tr/analiz/hisse/Sayfalar/Temel-Degerler-Ve-Oranlar.aspx"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            tables = pd.read_html(StringIO(response.text))
            all_tickers = []
            for t in tables:
                # Tablolardaki "Kod" sütunlarını kontrol edip birleştiriyoruz
                if "Kod" in t.columns:
                    all_tickers.extend(t["Kod"].dropna().astype(str).tolist())
            
            for t in all_tickers:
                if len(t.strip()) >= 2:
                    bist_list.append(t.strip() + ".IS")
                    
            bist_list = list(set(bist_list))
    except Exception as e:
        print("Is Yatirim Fetch Error:", e)

    # 2. YÖNTEM (YEDEK): KAP üzerinden çekmeyi dene
    if len(bist_list) < 100:
        try:
            import requests
            import re
            url = "https://www.kap.org.tr/tr/bist-sirketler"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                clean_text = response.text.replace('\\\\', '')
                all_tickers = re.findall(r'\"stockCode\":\"([A-Z0-9, ]+)\"', clean_text)
                
                for t in all_tickers:
                    for sub_t in str(t).split(','):
                        sub_t = sub_t.strip()
                        if len(sub_t) > 1:
                            bist_list.append(sub_t + ".IS")
                
                bist_list = list(set(bist_list))
        except Exception as e:
            print("KAP Fetch Error:", e)

    # Hisseler başarıyla bulunduysa doğrula
    if len(bist_list) > 100:
        import yfinance as yf
        try:
            # Sadece Yahoo'da veri sağlayan aktif (delisted olmayan) hisseleri filtrele
            data = yf.download(bist_list, period="1d", threads=True, progress=False)
            valid_tickers = data['Close'].dropna(axis=1, how='all').columns.tolist()
            
            if len(valid_tickers) > 100:
                return sorted(valid_tickers)
        except Exception as inner_e:
            print("YF Download Filter Error:", inner_e)
            
        return sorted(bist_list)
        
    # En kötü senaryo: Siteler engellediyse Fallback (Yedek) Liste
    return [
        "AKBNK.IS", "ARCLK.IS", "ASELS.IS", "BIMAS.IS", "DOHOL.IS", 
        "EKGYO.IS", "EREGL.IS", "FROTO.IS", "GARAN.IS", "GUBRF.IS", 
        "HALKB.IS", "HEKTS.IS", "ISCTR.IS", "KCHOL.IS", "KOZAA.IS", 
        "KOZAL.IS", "KRDMD.IS", "PETKM.IS", "PGSUS.IS", "SAHOL.IS", 
        "SASA.IS",  "SISE.IS",  "TAVHL.IS", "TCELL.IS", "THYAO.IS", 
        "TKFEN.IS", "TOASO.IS", "TTKOM.IS", "TUPRS.IS", "VAKBN.IS", 
        "YKBNK.IS"
    ]

# Config dosyasını devre dışı bıraktık, dinamik olarak çekiyoruz:
bist_stocks = get_all_bist_tickers()

st.sidebar.header("Filtre Seçenekleri")
selected_stock = st.sidebar.selectbox("Bir BIST Hisse Senedi Seçin", bist_stocks)
period = "1y"

@st.cache_data(ttl=24*3600) # cache for 1 day
def load_stock_data(ticker):
    # Sadece history bilgisini çekiyoruz, .info() kısmı banlanmalara neden oluyor.
    stock = yf.Ticker(ticker)
    hist = stock.history(period=period)
    return hist

if selected_stock:
    st.write(f"### **{selected_stock}** için veriler getiriliyor")
    
    with st.spinner('Yahoo Finance üzerinden veriler yükleniyor...'):
        try:
            hist_data = load_stock_data(selected_stock)
            
            # Bazı eski, yayından kaldırılmış (delisted) veya Yahoo'nun henüz veri akışını
            # sağlamadığı hisselerde dönen hata Rate Limit gibi görünebiliyor ve hist_data.empty geliyor.
            if hist_data is None or len(hist_data) == 0:
                st.warning(f"⚠️ **{selected_stock}** için şu an geçmiş veri bulunamadı. Bu hisse senedi borsa kotundan çıkmış, Yahoo Finance sisteminde henüz güncellenmemiş veya tamamen farklı bir isme sahip olabilir.")
            else:
                # BIST hisseleri TRY bazındadır. Arama engelini aşmak için info sorgulamasını kaldırdık.
                currency = "TRY"
                long_name = selected_stock.replace(".IS", " Hisse Senedi")
                
                # Metrics
                current_price = hist_data['Close'][-1]
                prev_price = hist_data['Close'][-2] if len(hist_data) > 1 else current_price
                price_change = current_price - prev_price
                pct_change = (price_change / prev_price) * 100
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Güncel Fiyat", f"{current_price:.2f} {currency}", f"{price_change:.2f} ({pct_change:.2f}%)")
                col2.metric("Para Birimi", currency)
                col3.write(f"**Şirket:** {long_name}")

                st.markdown("---")
                
                # Interactive Plotly Chart
                st.subheader(f"{selected_stock} - Son 1 Yıllık Fiyat Grafiği")
                
                fig = go.Figure()
                fig.add_trace(go.Candlestick(
                    x=hist_data.index,
                    open=hist_data['Open'],
                    high=hist_data['High'],
                    low=hist_data['Low'],
                    close=hist_data['Close'],
                    name='Piyasa Verileri',
                    hovertemplate="<b>Tarih:</b> %{x|%d.%m.%Y}<br>" +
                                  "<b>Açılış:</b> %{open:.2f}<br>" +
                                  "<b>En Yüksek:</b> %{high:.2f}<br>" +
                                  "<b>En Düşük:</b> %{low:.2f}<br>" +
                                  "<b>Kapanış:</b> %{close:.2f}<extra></extra>"
                ))
                
                fig.update_layout(
                    title=f"{selected_stock} Geçmiş Fiyatları",
                    yaxis_title=f"Fiyat ({currency})",
                    xaxis_title="",
                    autosize=True,
                    height=500,
                    margin=dict(l=10, r=10, b=20, t=100), # Üst boşluğu (t=100) arttırdık ki butonlar grafiğin veya başlığın üstüne binmesin
                    xaxis_rangeslider_visible=False,
                    xaxis=dict(
                        tickformat="%d.%m.%Y",
                        tickangle=-90,
                        dtick=604800000,
                        rangeselector=dict(
                            visible=True,
                            x=1, # 0 sol, 1 sağ demektir. Sağa hizalıyoruz.
                            y=1.1, # Butonları grafiğin DIŞINA (üstüne) taşır
                            xanchor="right", # Sağdan hizalama çılası
                            yanchor="bottom",
                            buttons=list([
                                dict(count=1, label="1A", step="month", stepmode="backward"),
                                dict(count=3, label="3A", step="month", stepmode="backward"),
                                dict(count=6, label="6A", step="month", stepmode="backward"),
                                dict(step="all", label="Tümü")
                            ])
                        )
                    )
                )
                
                # responsive: True ile her cihaza tam oturmasını sağlıyoruz, mobildeki gereksiz menü barını da gizliyoruz.
                st.plotly_chart(fig, use_container_width=True, config={'locale': 'tr', 'responsive': True, 'displayModeBar': False})
                
        except Exception as e:
            # Gelen hata sadece Too Many Requests hatası olabilir ve aslında Yahoo o hisseyi bulamayınca da aynı hatayı zoraki yansıtıyor.
            # O yüzden hatayı ezip temiz uyarı çıkarıyoruz.
            st.warning(f"⚠️ **{selected_stock}** güncel verilerine ulaşılamadı. Sembol Yahoo Finance'te aktif olmayabilir (" + str(e).split()[0] + ")")

st.sidebar.markdown("---")
st.sidebar.info("Veriler yfinance tarafından sağlanmaktadır. Son 1 yıllık geçmiş veriler günlük olarak yenilenir.")

