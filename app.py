import datetime
import pandas as pd
import streamlit as st
from supabase import create_client

# ---------------------------------------------------------
# SETUP & MOBILE CONFIG
# ---------------------------------------------------------
st.set_page_config(
    page_title="ระบบสต็อก",
    page_icon="🏪",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Custom CSS สำหรับให้แสดงผลพอดีจอมือถือ
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
    }
    h1 { font-size: 1.4rem !important; margin-bottom: 0.2rem !important; }
    h2, h3 { font-size: 1.1rem !important; }
    
    /* สไตล์ปุ่มแท็บเลือกเมนูด้านบน */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        padding-left: 8px;
        padding-right: 8px;
        font-size: 0.85rem;
    }
    
    /* ซ่อนแถบฟุตเตอร์ที่ไม่จำเป็น */
    footer {visibility: hidden;}
    </style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# 1. CONNECT TO SUPABASE
# ---------------------------------------------------------
@st.cache_resource
def init_supabase():
  url = st.secrets["SUPABASE_URL"]
  key = st.secrets["SUPABASE_KEY"]
  return create_client(url, key)


supabase = init_supabase()

st.title("🏪 ระบบสต็อก")
st.caption("ข้อมูลบันทึกถาวรบน Supabase | ตัดสต็อก FIFO")

# ---------------------------------------------------------
# 2. MAIN NAVIGATION (ใช้ TABS ด้านบน)
# ---------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(
    ["💰 สรุปกำไร", "🛒 บันทึกขาย", "📥 รับสต็อก", "📦 ดูสต็อก"]
)

# ---------------------------------------------------------
# TAB 1: สรุปงวดกำไร & แบ่งปันผล
# ---------------------------------------------------------
with tab1:
  st.subheader("💰 สรุปงวดปัจจุบัน (ยังไม่ตัดรอบ)")

  response = (
      supabase.table("sales").select("*").eq("settled", False).execute()
  )
  sales_data = response.data
  current_sales = pd.DataFrame(sales_data) if sales_data else pd.DataFrame()

  total_sales = (
      float(current_sales["total_sales"].sum())
      if not current_sales.empty
      else 0.0
  )
  total_cost = (
      float(current_sales["total_cost"].sum())
      if not current_sales.empty
      else 0.0
  )
  net_profit = (
      float(current_sales["net_profit"].sum())
      if not current_sales.empty
      else 0.0
  )
  profit_per_person = net_profit / 2.0

  c1, c2 = st.columns(2)
  c1.metric("ยอดขายรวม", f"฿{total_sales:,.2f}")
  c2.metric("ต้นทุนรวม", f"฿{total_cost:,.2f}")

  c3, c4 = st.columns(2)
  c3.metric("กำไรสุทธิ", f"฿{net_profit:,.2f}")
  c4.metric("แบ่งคนละ (50%)", f"฿{profit_per_person:,.2f}")

  st.markdown("---")

  if st.button("🔘 กดสรุป & ตัดรอบแบ่งกำไร", type="primary", use_container_width=True):
    if current_sales.empty:
      st.warning("ยังไม่มีรายการขายในงวดนี้")
    else:
      settle_id = f"SETTL-{int(datetime.datetime.now().timestamp())}"
      now_str = datetime.datetime.now().isoformat()

      supabase.table("settlements").insert({
          "settlement_id": settle_id,
          "settle_date": now_str,
          "total_sales": total_sales,
          "total_cost": total_cost,
          "net_profit": net_profit,
          "profit_per_partner": profit_per_person,
      }).execute()

      supabase.table("sales").update({"settled": True}).eq(
          "settled", False
      ).execute()

      st.balloons()
      st.success(f"ตัดรอบสำเร็จ! แบ่งปันผลคนละ ฿{profit_per_person:,.2f}")
      st.rerun()

  st.caption("⚡ การตัดรอบจะรีเซ็ทยอดกำไรเป็น 0 เริ่มนับใหม่ แต่สต็อกสินค้าคงเหลือเท่าเดิม")

  st.markdown("---")
  st.subheader("📋 รายการขายงวดนี้")
  if not current_sales.empty:
    st.dataframe(current_sales, use_container_width=True)
  else:
    st.info("ยังไม่มีรายการขายในงวดปัจจุบัน")

  st.markdown("---")
  st.subheader("📜 ประวัติการตัดรอบย้อนหลัง")
  settle_res = (
      supabase.table("settlements")
      .select("*")
      .order("settle_date", desc=True)
      .execute()
  )
  if settle_res.data:
    st.dataframe(pd.DataFrame(settle_res.data), use_container_width=True)

# ---------------------------------------------------------
# TAB 2: บันทึกการขายหน้าร้าน
# ---------------------------------------------------------
with tab2:
  st.subheader("🛒 บันทึกรายการขายสินค้า")

  prods = supabase.table("products").select("*").execute().data
  lots = (
      supabase.table("stock_lots")
      .select("*")
      .gt("remaining_qty", 0)
      .order("buy_date")
      .execute()
      .data
  )

  if not prods:
    st.warning("กรุณาเพิ่มรายการสินค้าก่อน")
  else:
    prods_df = pd.DataFrame(prods)
    lots_df = pd.DataFrame(lots) if lots else pd.DataFrame()

    if not lots_df.empty:
      stock_summary = (
          lots_df.groupby("product_id")["remaining_qty"].sum().reset_index()
      )
      prods_df = pd.merge(
          prods_df, stock_summary, on="product_id", how="left"
      ).fillna({"remaining_qty": 0})
    else:
      prods_df["remaining_qty"] = 0

    cup_prod = prods_df[
        prods_df["product_name"].str.contains("แก้วกระดาษ|แก้ว", na=False)
    ]
    cup_available = not cup_prod.empty

    with st.form("sale_form", clear_on_submit=True):
      prod_options = {
          row[
              "product_name"
          ]: f"{row['product_name']} (เหลือ: {int(row['remaining_qty'])} {row['unit']})"
          for _, row in prods_df.iterrows()
      }
      selected_prod_name = st.selectbox(
          "เลือกสินค้า",
          options=list(prod_options.keys()),
          format_func=lambda x: prod_options[x],
      )

      selected_prod = prods_df[
          prods_df["product_name"] == selected_prod_name
      ].iloc[0]
      p_id = selected_prod["product_id"]
      available_qty = int(selected_prod["remaining_qty"])
      unit_name = selected_prod["unit"]
      sell_price = float(selected_prod["selling_price"])

      col1, col2 = st.columns(2)
      sell_qty = col1.number_input(
          f"จำนวน ({unit_name})",
          min_value=1,
          max_value=max(1, available_qty),
          value=1,
      )
      custom_price = col2.number_input(
          "ราคา/หน่วย (บาท)", min_value=0.0, value=sell_price
      )

      include_cup = False
      if cup_available:
        cup_row = cup_prod.iloc[0]
        cup_rem = int(cup_row["remaining_qty"])
        include_cup = st.checkbox(
            f"🥤 รับ 'แก้วกระดาษ' ด้วย (+{sell_qty} ใบ) [คงเหลือ: {cup_rem} ใบ]"
        )

      btn_submit_sale = st.form_submit_button("💾 บันทึกการขาย", type="primary", use_container_width=True)

      if btn_submit_sale:
        if available_qty < sell_qty:
          st.error(f"สินค้าคงเหลือไม่พอ (มี {available_qty} {unit_name})")
        else:
          def deduct_stock_fifo(prod_id, qty_needed):
            avail_lots = [lot for lot in lots if lot["product_id"] == prod_id]
            used_lots_cost = 0.0
            remaining_to_deduct = qty_needed

            for lot in avail_lots:
              if remaining_to_deduct <= 0:
                break
              lot_id = lot["lot_id"]
              lot_rem = int(lot["remaining_qty"])
              unit_cost = float(lot["unit_cost"])

              take_qty = min(remaining_to_deduct, lot_rem)
              used_lots_cost += take_qty * unit_cost

              supabase.table("stock_lots").update(
                  {"remaining_qty": lot_rem - take_qty}
              ).eq("lot_id", lot_id).execute()
              remaining_to_deduct -= take_qty

            return used_lots_cost

          main_cost = deduct_stock_fifo(p_id, sell_qty)

          cup_cost = 0.0
          if include_cup and cup_available:
            cup_p_id = cup_prod.iloc[0]["product_id"]
            cup_cost = deduct_stock_fifo(cup_p_id, sell_qty)

          tot_sales = sell_qty * custom_price
          tot_cost = main_cost + cup_cost
          net_prof = tot_sales - tot_cost

          sale_id = f"SALE-{int(datetime.datetime.now().timestamp())}"
          sale_item_name = (
              f"{selected_prod_name} (+แก้ว)"
              if include_cup
              else selected_prod_name
          )

          supabase.table("sales").insert({
              "sale_id": sale_id,
              "product_id": p_id,
              "product_name": sale_item_name,
              "qty": sell_qty,
              "unit_cost": tot_cost / sell_qty if sell_qty > 0 else 0,
              "selling_price": custom_price,
              "total_sales": tot_sales,
              "total_cost": tot_cost,
              "net_profit": net_prof,
              "settled": False,
          }).execute()

          st.toast(f"✅ บันทึกขาย {sale_item_name} สำเร็จ!", icon="🎉")
          st.success(f"บันทึกขาย {sale_item_name} เรียบร้อยแล้ว (รีเซ็ตหน้าจอแล้ว)")
          st.rerun()

# ---------------------------------------------------------
# TAB 3: บันทึกรับสินค้าเข้าสต็อก
# ---------------------------------------------------------
with tab3:
  st.subheader("📥 บันทึกรับสินค้าเข้าสต็อก")

  sub_tab1, sub_tab2 = st.tabs(["ซื้อเข้าสต็อก (ล็อตใหม่)", "เพิ่ม/ลบชื่อสินค้า"])

  with sub_tab1:
    prods = supabase.table("products").select("*").execute().data
    if not prods:
      st.warning("กรุณาเพิ่มชื่อสินค้าใหม่ก่อน")
    else:
      with st.form("add_lot_form", clear_on_submit=True):
        prod_names = [p["product_name"] for p in prods]
        p_name = st.selectbox("เลือกสินค้า", prod_names)

        buy_date = st.date_input("วันที่รับเข้า", datetime.date.today())
        supplier = st.text_input("แหล่งซื้อ", "")

        col_c, col_d = st.columns(2)
        tot_price = col_c.number_input("ราคารวม (บาท)", min_value=0.0, value=0.0, step=10.0)
        tot_qty = col_d.number_input("จำนวนที่ได้", min_value=1, value=1)

        calculated_unit_cost = tot_price / tot_qty if tot_qty > 0 else 0.0
        st.info(f"💡 ทุนต่อหน่วย = **฿{calculated_unit_cost:,.2f}** บาท")

        btn_add_lot = st.form_submit_button("บันทึกเข้าสต็อก", use_container_width=True)

        if btn_add_lot:
          if tot_price <= 0:
            st.error("กรุณากรอกราคารวมที่ซื้อมาด้วยครับ")
          else:
            p_id = [p["product_id"] for p in prods if p["product_name"] == p_name][0]
            lot_id = f"LOT-{int(datetime.datetime.now().timestamp())}"

            supabase.table("stock_lots").insert({
                "lot_id": lot_id,
                "product_id": p_id,
                "buy_date": str(buy_date),
                "supplier": supplier,
                "total_price": tot_price,
                "total_qty": tot_qty,
                "unit_cost": calculated_unit_cost,
                "remaining_qty": tot_qty,
            }).execute()

            st.toast(f"✅ เพิ่มสต็อก {p_name} สำเร็จ!", icon="📦")
            st.success(f"บันทึกรับสต็อก {p_name} จำนวน {tot_qty} หน่วย เรียบร้อยแล้ว")
            st.rerun()

  with sub_tab2:
    st.markdown("##### ➕ เพิ่มชื่อสินค้าใหม่")
    with st.form("add_product_form", clear_on_submit=True):
      new_p_name = st.text_input("ชื่อสินค้าใหม่", placeholder="เช่น กาแฟซอง, แก้วกระดาษ")
      new_unit = st.selectbox("หน่วยนับ", ["ขวด", "ซอง", "ห่อ", "ชิ้น", "กล่อง", "ใบ"])
      default_sell_price = st.number_input("ราคาขายตั้งต้น (บาท)", min_value=0.0, value=0.0, step=1.0)

      btn_add_prod = st.form_submit_button("เพิ่มสินค้า", use_container_width=True)

      if btn_add_prod:
        if not new_p_name.strip():
          st.error("กรุณาพิมพ์ชื่อสินค้าก่อนกดบันทึกครับ")
        else:
          new_p_id = f"P-{int(datetime.datetime.now().timestamp())}"
          supabase.table("products").insert({
              "product_id": new_p_id,
              "product_name": new_p_name.strip(),
              "unit": new_unit,
              "selling_price": default_sell_price,
          }).execute()

          st.toast(f"✅ เพิ่มสินค้า '{new_p_name}' แล้ว!", icon="✨")
          st.success(f"เพิ่มสินค้า '{new_p_name}' เรียบร้อยแล้ว")
          st.rerun()

    st.markdown("---")
    st.markdown("##### 🗑️ รายชื่อสินค้าในระบบ (กดลบได้)")
    all_prods = supabase.table("products").select("*").execute().data
    if all_prods:
      for p in all_prods:
        col_name, col_del = st.columns([3, 1])
        col_name.write(f"• **{p['product_name']}** ({p['unit']}) - {p['selling_price']}บ.")
        if col_del.button("🗑️ ลบ", key=f"del_{p['product_id']}", use_container_width=True):
          supabase.table("products").delete().eq("product_id", p["product_id"]).execute()
          st.toast(f"ลบ {p['product_name']} แล้ว", icon="🗑️")
          st.rerun()
    else:
      st.info("ยังไม่มีรายชื่อสินค้าในระบบ")

# ---------------------------------------------------------
# TAB 4: ดูสต็อกสินค้าคงเหลือ
# ---------------------------------------------------------
with tab4:
  st.subheader("📦 สต็อกสินค้าคงเหลือ")

  lots_res = supabase.table("stock_lots").select("*").execute()
  prods_res = supabase.table("products").select("*").execute()

  if lots_res.data and prods_res.data:
    lots_df = pd.DataFrame(lots_res.data)
    prods_df = pd.DataFrame(prods_res.data)

    # รวมตารางเอาชื่อสินค้ามาแสดง
    merged = pd.merge(lots_df, prods_df, on="product_id", how="left")

    # เลือกคอลัมน์: ชื่อสินค้า, ราคาทุน/หน่วย, แหล่งซื้อ, จำนวนรับเข้า, จำนวนคงเหลือ, หน่วย
    display_df = merged[[
        "product_name",
        "unit_cost",
        "supplier",
        "total_qty",
        "remaining_qty",
        "unit",
    ]].copy()

    display_df.columns = [
        "ชื่อสินค้า",
        "ทุน/หน่วย",
        "ซื้อจาก",
        "จำนวนรับเข้า",
        "จำนวนคงเหลือ",
        "หน่วย",
    ]

    # จัดรูปแบบตัวเลขให้อ่านง่าย
    display_df["ทุน/หน่วย"] = display_df["ทุน/หน่วย"].map("฿{:,.2f}".format)
    display_df["จำนวนรับเข้า"] = display_df["จำนวนรับเข้า"].astype(int)
    display_df["จำนวนคงเหลือ"] = display_df["จำนวนคงเหลือ"].astype(int)
    display_df["ซื้อจาก"] = display_df["ซื้อจาก"].fillna("-")

    st.dataframe(display_df, use_container_width=True, hide_index=True)
  else:
    st.info("ยังไม่มีข้อมูลสต็อกสินค้า")
