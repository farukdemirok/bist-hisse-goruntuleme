# ----------------------------------- #
# LIBRARIES 
# ----------------------------------- #
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from config import bist_stocks

st.set_page_config(page_title="BIST Hisse Senedi Görüntüleyici", layout="wide", page_icon="📈")
st.title("📈 BIST Hisse Senedi Görüntüleyici")

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
            
            if hist_data.empty:
                st.error("Bu hisse senedi için veri bulunamadı. Borsa kotundan çıkmış veya aktif olmayabilir.")
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
                    margin=dict(l=10, r=10, b=20, t=50), # Kenar boşluklarını daraltarak mobil ekrana sığdırdık
                    xaxis_rangeslider_visible=False,
                    xaxis_tickformat="%d.%m.%Y",
                    xaxis_tickangle=-90, # Daha sık etiket olacağı için dikey (90 derece) yapmak daha temiz gösterir
                    xaxis_dtick=604800000  # 7 days in milliseconds (Tekrar haftalık gösterim eklendi)
                )
                
                # responsive: True ile her cihaza tam oturmasını sağlıyoruz, mobildeki gereksiz menü barını da gizliyoruz.
                st.plotly_chart(fig, use_container_width=True, config={'locale': 'tr', 'responsive': True, 'displayModeBar': False})
                
        except Exception as e:
            st.error(f"Veri getirme başarısız oldu: {str(e)}")

st.sidebar.markdown("---")
st.sidebar.info("Veriler yfinance tarafından sağlanmaktadır. Son 1 yıllık geçmiş veriler günlük olarak yenilenir.")

