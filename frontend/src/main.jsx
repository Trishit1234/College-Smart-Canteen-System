import React, { createContext, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes, Route, NavLink, useNavigate } from 'react-router-dom';
import { UtensilsCrossed, ShoppingCart, Bell, Search, Plus, Minus, Trash2, LayoutDashboard, Package, Users, BarChart3, ClipboardList, LogOut, Clock, ImagePlus, Pencil, X, CreditCard } from 'lucide-react';
import { api, fetchAll } from './api';
import gcletLogo from './assets/gclet-college-logo.jpg';
import { DemoPaymentModal, PaymentHistory } from './payment-flow';
import './styles.css';
import './food-manager.css';
import './menu-status.css';
import './brand-logo.css';
import './campus-polish.css';

const AuthContext=createContext(null);
function AuthProvider({children}){
 const [user,setUser]=useState(()=>{try{return JSON.parse(localStorage.getItem('user'))}catch{return null}});
 const login=async(username,password)=>{
  const {data}=await api.post('/auth/login/',{username,password});
  localStorage.setItem('access',data.access);localStorage.setItem('refresh',data.refresh);localStorage.setItem('user',JSON.stringify(data.user));setUser(data.user);return data.user;
 };
 const logout=()=>{localStorage.clear();setUser(null)};
 return <AuthContext.Provider value={{user,login,logout,setUser}}>{children}</AuthContext.Provider>;
}
const useAuth=()=>useContext(AuthContext);

function Layout({children}){
 const {user,logout}=useAuth();const nav=useNavigate();
 const links=user?[
  ['Menu','/menu',UtensilsCrossed],['Orders','/orders',ClipboardList],['Payments','/payments',CreditCard],
  ...(user.role==='STAFF'?[['Staff','/staff',Package]]:[]),
  ...(user.role==='ADMIN'?[['Admin','/admin',LayoutDashboard],['Manage food','/admin/menu',Package]]:[])
 ]:[['Home','/',UtensilsCrossed]];
 return <div className="app-shell">
  <aside className="sidebar">
   <button className="brand" onClick={()=>nav(user?'/menu':'/')}><img className="brand-logo" src={gcletLogo} alt="GCLET college emblem"/><div><strong>GCLET</strong><small>Smart Canteen</small></div></button>
   <nav>{links.map(([label,path,Icon])=><NavLink key={path} to={path} className={({isActive})=>isActive?'nav-link active':'nav-link'}><Icon size={19}/>{label}</NavLink>)}</nav>
   {user&&<div className="sidebar-profile"><div className="avatar">{user.first_name?.[0]||user.username[0].toUpperCase()}</div><div><strong>{user.first_name||user.username}</strong><small>{user.role}</small></div><button onClick={()=>{logout();nav('/')}}><LogOut size={17}/></button></div>}
  </aside>
  <main><header className="topbar"><div className="header-brand"><img className="header-logo" src={gcletLogo} alt="GCLET college emblem"/><div className="header-brand-copy"><strong>Government College of Engineering and Leather Technology</strong><span>Campus dining · Smart Canteen</span></div></div><div className="top-actions">{user&&<button className="icon-btn" title="Cart" onClick={()=>nav('/cart')}><ShoppingCart size={20}/></button>}<button className="icon-btn"><Bell size={20}/><i/></button>{!user&&<><button className="btn ghost" onClick={()=>nav('/login')}>Log in</button><button className="btn primary" onClick={()=>nav('/register')}>Register</button></>}</div></header><div className="content">{children}</div></main>
 </div>;
}

function Landing(){
 const [items,setItems]=useState([]);const nav=useNavigate();
 useEffect(()=>{fetchAll('/food/',{featured:true,available:true}).then(setItems).catch(()=>{})},[]);
 const featured=items[0];
 return <div><section className="hero"><div><span className="pill">Now accepting online orders</span><h1>Fresh food.<br/><em>Zero waiting.</em></h1><p>Order your favorite campus meals and collect them at your chosen time.</p><div className="hero-actions"><button className="btn primary" onClick={()=>nav('/menu')}>Order now</button><button className="btn ghost" onClick={()=>nav('/register')}>Create account</button></div></div><div className="hero-card">{featured?<><div className="hero-dish">{featured.image?<img src={featured.image} alt={featured.name}/>:<UtensilsCrossed size={64}/>}</div><div><small>Featured today</small><strong>{featured.name}</strong><span>₹{featured.effective_price} · {featured.preparation_time} min</span></div></>:<div className="hero-dish"><UtensilsCrossed size={64}/></div>}</div></section>
 <section><div className="section-head"><div><span className="eyebrow">Featured menu</span><h2>Popular today</h2></div></div><div className="food-grid">{items.slice(0,4).map(item=><FoodCard key={item.id} item={item} />)}</div></section></div>;
}

function FoodCard({item}){
 const {user}=useAuth();const nav=useNavigate();const [feedback,setFeedback]=useState('');
 const add=async()=>{if(!user){nav('/login');return}try{await api.post('/cart/add/',{item:item.id,quantity:1});setFeedback('Added to cart')}catch(err){setFeedback(err.response?.data?.detail||'Could not add item')}};
 return <article className="food-card"><div className="food-visual">{item.image?<img src={item.image} alt={item.name} loading="lazy"/>:<UtensilsCrossed size={45} />}{item.featured&&<span>Popular</span>}</div><div className="food-info"><div><h3>{item.name}</h3><small>{item.category_name}</small></div><p>{item.description}</p><div className="food-footer"><strong>₹{item.effective_price}</strong><button className="add-btn" onClick={add} disabled={!item.available||item.stock<1} title={!item.available||item.stock<1?'Out of stock':'Add to cart'}><Plus size={18}/></button></div><small className="stock-label">{feedback|| (item.stock>0?`${item.stock} available`:'Out of stock')}</small></div></article>;
}

function Menu(){
 const [items,setItems]=useState([]);const [categories,setCategories]=useState([]);const [search,setSearch]=useState('');const [category,setCategory]=useState('');
 useEffect(()=>{fetchAll('/categories/',{is_active:true}).then(setCategories).catch(()=>{})},[]);
 useEffect(()=>{let active=true;fetchAll('/food/',{search,category,available:true}).then(data=>{if(active)setItems(data)}).catch(()=>{});return()=>{active=false}},[search,category]);
 return <><div className="page-head"><div><span className="eyebrow">Browse menu</span><h1>What would you like?</h1></div></div><div className="toolbar"><label className="search"><Search size={18}/><input placeholder="Search food, dishes..." value={search} onChange={e=>setSearch(e.target.value)}/></label><select value={category} onChange={e=>setCategory(e.target.value)}><option value="">All categories</option>{categories.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></div><div className="food-grid">{items.map(item=><FoodCard key={item.id} item={item}/>)}</div>{!items.length&&<div className="empty panel">No available food matches your search.</div>}</>;
}

function Login(){
 const {login}=useAuth();const nav=useNavigate();const [form,setForm]=useState({username:'',password:''});const [error,setError]=useState('');
 const submit=async(e)=>{e.preventDefault();setError('');try{const u=await login(form.username,form.password);nav(u.role==='ADMIN'?'/admin':u.role==='STAFF'?'/staff':'/menu')}catch(err){setError(err.response?.data?.detail||'Invalid login details')}};
 return <AuthCard title="Welcome back"><form onSubmit={submit}><label>Username<input value={form.username} onChange={e=>setForm({...form,username:e.target.value})} required/></label><label>Password<input type="password" value={form.password} onChange={e=>setForm({...form,password:e.target.value})} required/></label>{error&&<div className="error">{error}</div>}<button className="btn primary wide">Log in</button></form></AuthCard>;
}
function Register(){
 const [form,setForm]=useState({username:'',password:'',email:'',first_name:'',role:'STUDENT',college_id:''});const [msg,setMsg]=useState('');const nav=useNavigate();
 const submit=async(e)=>{e.preventDefault();setMsg('');try{await api.post('/auth/register/',form);setMsg('Account created. You can now log in.')}catch(err){setMsg(JSON.stringify(err.response?.data||'Registration failed'))}};
 return <AuthCard title="Create account"><form onSubmit={submit}><label>Full name<input value={form.first_name} onChange={e=>setForm({...form,first_name:e.target.value})} required/></label><label>Username<input value={form.username} onChange={e=>setForm({...form,username:e.target.value})} required/></label><label>Email<input type="email" value={form.email} onChange={e=>setForm({...form,email:e.target.value})}/></label><label>College ID<input value={form.college_id} onChange={e=>setForm({...form,college_id:e.target.value})}/></label><label>Account type<select value={form.role} onChange={e=>setForm({...form,role:e.target.value})}><option value="STUDENT">Student</option><option value="FACULTY">Faculty</option></select></label><label>Password<input type="password" value={form.password} onChange={e=>setForm({...form,password:e.target.value})} minLength={8} required/></label>{msg&&<div className="notice">{msg}</div>}<button className="btn primary wide">Register</button></form></AuthCard>;
}
function AuthCard({title,children}){return <div className="auth-wrap"><div className="auth-card"><div className="brand centered"><img className="brand-logo" src={gcletLogo} alt="GCLET college emblem"/><strong>GCLET Canteen</strong></div><h2>{title}</h2>{children}</div></div>}

function Cart(){
 const nav=useNavigate();
 const [cart,setCart]=useState(null);
 const [slots,setSlots]=useState([]);
 const [slot,setSlot]=useState('');
 const [coupon,setCoupon]=useState('');
 const [message,setMessage]=useState('');
 const [pendingOrder,setPendingOrder]=useState(null);
 const [showPayment,setShowPayment]=useState(false);
 const [checkoutBusy,setCheckoutBusy]=useState(false);
 const checkoutKey=useRef(null);
 const load=()=>api.get('/cart/').then(r=>setCart(r.data));
 useEffect(()=>{load().catch(()=>setMessage('Could not load your cart. Please refresh and try again.'))},[]);
 useEffect(()=>{api.get('/pickup-slots/').then(r=>setSlots(r.data.results||r.data)).catch(()=>setMessage('Could not load pickup times. Please refresh and try again.'))},[]);
 const update=async(ci,q)=>{try{const r=await api.post('/cart/set_quantity/',{cart_item:ci.id,quantity:q});setCart(r.data);setMessage('')}catch(error){setMessage(error.response?.data?.detail||'Could not update your cart.')}};
 const checkout=async(method)=>{
  if(!slot){setMessage('Choose a pickup slot before checkout.');return}
  if(checkoutBusy)return;
  setCheckoutBusy(true);setMessage('');
  if(!checkoutKey.current)checkoutKey.current=window.crypto.randomUUID();
  try{
   const {data}=await api.post('/checkout/',{
    pickup_slot:slot,coupon_code:coupon,payment_method:method,idempotency_key:checkoutKey.current,
   });
   checkoutKey.current=null;
   setCart({items:[]});setPendingOrder(data);
   if(method==='CASH'){
    setMessage(`Order ${data.number} placed. Pay at the counter when collecting.`);
   }else{
    setShowPayment(true);
   }
  }catch(error){
   setMessage(error.response?.data?.detail||'Checkout could not be completed. Your cart is unchanged; please retry.');
  }finally{setCheckoutBusy(false)}
 };
 const items=cart?.items||[];
 const subtotal=items.reduce((sum,item)=>sum+Number(item.item_detail.effective_price)*item.quantity,0);
 const tax=subtotal*.05;
 return <>
  <div className="page-head"><div><span className="eyebrow">Checkout</span><h1>Your cart</h1></div></div>
  {message&&<div className="notice cart-message" role="status">{message}</div>}
  {pendingOrder&&<section className="pending-payment-panel">
   <div><span className="eyebrow">{pendingOrder.status==='AWAITING PAYMENT'?'Payment needed':'Order placed'}</span><strong>{pendingOrder.number}</strong><small>{pendingOrder.status==='AWAITING PAYMENT'?'Your order is reserved. Complete the simulated test payment or return later to retry.':'Your order is with the canteen. Pay at the counter when collecting.'}</small></div>
   <div className="pending-payment-actions">
    {pendingOrder.status==='AWAITING PAYMENT'&&<button className="btn primary" type="button" onClick={()=>setShowPayment(true)}>Continue payment</button>}
    <button className="btn ghost" type="button" onClick={()=>nav('/orders')}>Track order</button>
   </div>
  </section>}
  <div className="cart-layout">
   <section className="panel">
    {items.length?items.map(item=><div className="cart-row" key={item.id}>
     <div className="cart-thumb">{item.item_detail.image?<img src={item.item_detail.image} alt={item.item_detail.name}/>:<UtensilsCrossed/>}</div>
     <div><strong>{item.item_detail.name}</strong><small>₹{item.item_detail.effective_price}</small></div>
     <div className="qty"><button type="button" onClick={()=>update(item,item.quantity-1)} aria-label={`Remove one ${item.item_detail.name}`}><Minus size={14}/></button><b>{item.quantity}</b><button type="button" onClick={()=>update(item,item.quantity+1)} aria-label={`Add one ${item.item_detail.name}`}><Plus size={14}/></button></div>
     <strong>₹{(item.item_detail.effective_price*item.quantity).toFixed(2)}</strong>
     <button className="trash" type="button" onClick={()=>update(item,0)} aria-label={`Remove ${item.item_detail.name}`}><Trash2 size={17}/></button>
    </div>):<div className="empty">{pendingOrder?'Your cart is clear; this order is saved above.':'Your cart is empty'}</div>}
   </section>
   <aside className="summary panel">
    <h3>Order summary</h3>
    <label>Pickup slot<select value={slot} onChange={event=>setSlot(event.target.value)}><option value="">Select pickup slot</option>{slots.map(pickupSlot=><option key={pickupSlot.id} value={pickupSlot.id}>{pickupSlot.name} · {pickupSlot.start_time.slice(0,5)}–{pickupSlot.end_time.slice(0,5)}</option>)}</select></label>
    <label>Coupon<input placeholder="WELCOME10" value={coupon} onChange={event=>setCoupon(event.target.value.toUpperCase())}/></label>
    <div className="totals"><p><span>Subtotal</span><b>₹{subtotal.toFixed(2)}</b></p><p><span>Estimated tax (5%)</span><b>₹{tax.toFixed(2)}</b></p><p className="grand"><span>Estimated total</span><b>₹{(subtotal+tax).toFixed(2)}</b></p></div>
    <div className="cart-test-note"><CreditCard size={16}/> Online checkout is simulated. No real payment is made.</div>
    {items.length>0&&<>
     <button className="btn primary wide" type="button" disabled={checkoutBusy} onClick={()=>checkout('UPI')}>{checkoutBusy?'Preparing checkout…':'Checkout with test payment'}</button>
     <button className="btn ghost wide cart-cash-button" type="button" disabled={checkoutBusy} onClick={()=>checkout('CASH')}>Pay cash at counter</button>
    </>}
   </aside>
  </div>
  {showPayment&&pendingOrder&&<DemoPaymentModal order={pendingOrder} onClose={()=>setShowPayment(false)} onPaymentComplete={()=>{setShowPayment(false);setPendingOrder(null);nav('/orders')}}/>}
 </>;
}

function Orders(){
 const [orders,setOrders]=useState([]);const [notifications,setNotifications]=useState([]);
 const [selectedPaymentOrder,setSelectedPaymentOrder]=useState(null);const [actionError,setActionError]=useState('');
 const load=()=>api.get('/orders/').then(r=>setOrders(r.data.results||r.data)).catch(()=>{});
 useEffect(()=>{load();api.get('/notifications/').then(r=>setNotifications(r.data.results||r.data)).catch(()=>{});const timer=setInterval(load,8000);return()=>clearInterval(timer)},[]);
 const cancel=async(id)=>{setActionError('');try{await api.post(`/orders/${id}/cancel/`);await load()}catch(error){setActionError(error.response?.data?.detail||'Could not cancel this order.')}};
 return <>
  <div className="page-head"><div><span className="eyebrow">Track purchases</span><h1>My orders</h1></div></div>
  {actionError&&<div className="payment-inline-error" role="alert">{actionError}</div>}
  <div className="orders-layout">
   <section>{orders.map(order=><article className="order-card" key={order.id}>
    <div className="order-title"><div><small>ORDER</small><strong>{order.number}</strong></div><span className={`status ${order.status.toLowerCase().replaceAll(' ','-')}`}>{order.status}</span></div>
    <div className="progress"><span className={['PENDING','CONFIRMED','PREPARING','READY FOR PICKUP','COMPLETED'].includes(order.status)?'done':''}/><span className={['CONFIRMED','PREPARING','READY FOR PICKUP','COMPLETED'].includes(order.status)?'done':''}/><span className={['PREPARING','READY FOR PICKUP','COMPLETED'].includes(order.status)?'done':''}/><span className={['READY FOR PICKUP','COMPLETED'].includes(order.status)?'done':''}/></div>
    <div className="order-products">{order.items.map(item=><span key={item.id}>{item.quantity}× {item.name}</span>)}</div>
    <div className="order-footer"><b>₹{order.total}</b><span className={`payment-status ${order.payment?.status==='PAID'?'paid':''}`}>{order.payment?.status||'Payment pending'}{order.payment?.test_mode&&order.payment?.method!=='CASH'?' · TEST':''}</span><small>{new Date(order.created_at).toLocaleString()}</small>
     {order.status==='AWAITING PAYMENT'&&<button className="btn primary" type="button" onClick={()=>setSelectedPaymentOrder(order)}>Retry simulated payment</button>}
     {['PENDING','CONFIRMED','AWAITING PAYMENT'].includes(order.status)&&order.payment?.status!=='PAID'&&<button className="btn ghost" type="button" onClick={()=>cancel(order.id)}>Cancel</button>}
    </div>
   </article>)}{!orders.length&&<div className="empty panel">No orders yet</div>}</section>
   <aside className="panel"><h3>Notifications</h3>{notifications.map(notification=><div className="notification" key={notification.id}><Bell size={17}/><div><strong>{notification.title}</strong><p>{notification.message}</p></div></div>)}{!notifications.length&&<p className="muted">No notifications</p>}</aside>
  </div>
  {selectedPaymentOrder&&<DemoPaymentModal order={selectedPaymentOrder} onClose={()=>setSelectedPaymentOrder(null)} onPaymentComplete={()=>{setSelectedPaymentOrder(null);load()}}/>}
 </>;
}

function Staff(){
 const [orders,setOrders]=useState([]);
 const load=()=>api.get('/orders/').then(r=>setOrders(r.data.results||r.data)).catch(()=>{});
 useEffect(()=>{load();const timer=setInterval(load,5000);return()=>clearInterval(timer)},[]);
 const action=async(id,type)=>{await api.post(`/orders/${id}/${type}/`,type==='reject'?{reason:'Unable to prepare requested item'}:{});load()};
 const setStatus=async(id,status)=>{await api.post(`/orders/${id}/status/`,{status,note:'Updated by canteen staff'});load()};
 return <><div className="page-head"><div><span className="eyebrow">Operations</span><h1>Staff order queue</h1></div><button className="btn primary" onClick={load}>Refresh</button></div><div className="staff-grid">{orders.map(o=><article className="staff-card" key={o.id}><div className="order-title"><div><small>{o.number}</small><strong>{o.customer_name}</strong></div><span className="status">{o.status}</span></div><div className="order-products">{o.items.map(i=><span key={i.id}>{i.quantity}× {i.name}</span>)}</div><div className="staff-actions">{o.status==='PENDING'&&<><button className="btn primary" onClick={()=>action(o.id,'accept')}>Accept</button><button className="btn ghost" onClick={()=>action(o.id,'reject')}>Reject</button></>}{o.status==='CONFIRMED'&&<button className="btn primary" onClick={()=>setStatus(o.id,'PREPARING')}>Start preparing</button>}{o.status==='PREPARING'&&<button className="btn primary" onClick={()=>setStatus(o.id,'READY FOR PICKUP')}>Mark ready</button>}{o.status==='READY FOR PICKUP'&&<button className="btn primary" onClick={()=>action(o.id,'complete')}>Mark collected</button>}</div></article>)}</div></>;
}

function Admin(){
 const [stats,setStats]=useState(null);const [tab,setTab]=useState('overview');const navigate=useNavigate();
 useEffect(()=>{api.get('/analytics/').then(r=>setStats(r.data)).catch(()=>{})},[]);
 const download=async(kind,fmt='csv')=>{
  const r=await api.get(`/reports/${kind}/`,{params:{format:fmt},responseType:'blob'});
  const url=URL.createObjectURL(r.data);const a=document.createElement('a');a.href=url;a.download=`${kind}-report.${fmt}`;a.click();URL.revokeObjectURL(url);
 };
 return <>
  <div className="page-head"><div><span className="eyebrow">Administration</span><h1>Business overview</h1></div>
   <div className="admin-head-actions"><button className="btn ghost" onClick={()=>navigate('/admin/menu')}>Add food</button>
    <div className="tabs">
     <button className={tab==='overview'?'active':''} onClick={()=>setTab('overview')}>Overview</button>
     <button className={tab==='payments'?'active':''} onClick={()=>setTab('payments')}>Transactions</button>
     <button className={tab==='reports'?'active':''} onClick={()=>setTab('reports')}>Reports</button>
    </div>
   </div>
  </div>
  {tab==='overview'&&<>
   <div className="stat-grid"><Stat label="Total revenue" value={`₹${stats?.total_revenue||0}`} icon={BarChart3}/><Stat label="Today's revenue" value={`₹${stats?.today_revenue||0}`} icon={Clock}/><Stat label="Total orders" value={stats?.total_orders||0} icon={ClipboardList}/><Stat label="Registered users" value={stats?.registered_users||0} icon={Users}/></div>
   <div className="admin-grid"><section className="panel"><h3>Order status</h3><div className="bar-chart">{[['Pending',stats?.pending_orders||0,'orange'],['Completed',stats?.completed_orders||0,'green'],['Cancelled',stats?.cancelled_orders||0,'red']].map(([label,value,color])=><div key={label}><span>{label}</span><div><i className={color} style={{width:`${Math.min(100,value*12)}%`}}/></div><b>{value}</b></div>)}</div></section><section className="panel"><h3>Popular items</h3>{stats?.popular_items?.length?stats.popular_items.map((item,index)=><div className="popular-row" key={index}><span>{index+1}</span><strong>{item.items__name||'Item'}</strong><b>{item.count} sold</b></div>):<p className="muted">No completed sales yet</p>}</section></div>
  </>}
  {tab==='payments'&&<PaymentHistory compact/>}
  {tab==='reports'&&<section className="panel report-panel"><h3>Download reports</h3><div className="report-actions"><button className="btn primary" onClick={()=>download('sales','csv')}>Sales CSV</button><button className="btn primary" onClick={()=>download('orders','pdf')}>Orders PDF</button><button className="btn primary" onClick={()=>download('inventory','csv')}>Inventory CSV</button></div></section>}
 </>;
}
function Stat({label,value,icon:Icon}){return <article className="stat-card"><div className="stat-icon"><Icon size={21}/></div><small>{label}</small><strong>{value}</strong></article>}

function FoodManager(){
 const empty={name:'',description:'',category:'',price:'',discounted_price:'',stock:'0',preparation_time:'15',is_vegetarian:true,available:true,featured:false,allergens:''};
 const [items,setItems]=useState([]);const [categories,setCategories]=useState([]);const [form,setForm]=useState(empty);const [photo,setPhoto]=useState(null);const [editing,setEditing]=useState(null);const [notice,setNotice]=useState('');const [error,setError]=useState('');
 const load=async()=>{const [foods,cats]=await Promise.all([fetchAll('/food/'),fetchAll('/categories/',{is_active:true})]);setItems(foods);setCategories(cats)};
 useEffect(()=>{load().catch(()=>setError('Could not load catalogue.'))},[]);
 const edit=(item)=>{setEditing(item.id);setForm({name:item.name,description:item.description,category:String(item.category),price:item.price,discounted_price:item.discounted_price||'',stock:String(item.stock),preparation_time:String(item.preparation_time),is_vegetarian:item.is_vegetarian,available:item.available,featured:item.featured,allergens:item.allergens||''});setPhoto(null);setNotice('');setError('');window.scrollTo({top:0,behavior:'smooth'})};
 const reset=()=>{setEditing(null);setForm({...empty,category:categories[0]?String(categories[0].id):''});setPhoto(null)};
 const save=async(e)=>{e.preventDefault();setError('');setNotice('');if(photo&&photo.size>5*1024*1024){setError('Choose an image smaller than 5 MB.');return}const data=new FormData();Object.entries(form).forEach(([key,value])=>data.append(key,value===null?'':String(value)));if(photo)data.append('image',photo);try{const url=editing?`/food/${editing}/`:'/food/';await api.request({url,method:editing?'patch':'post',data});setNotice(editing?'Food item updated.':'Food item added to the menu.');reset();await load()}catch(err){const payload=err.response?.data;setError(typeof payload==='object'?Object.entries(payload).map(([k,v])=>`${k}: ${v}`).join(' · '):'Could not save food item. Check the form and try again.')}}
 const remove=async(item)=>{if(!window.confirm(`Delete ${item.name}?`))return;setError('');try{await api.delete(`/food/${item.id}/`);setNotice(`${item.name} deleted.`);await load()}catch(err){setError(err.response?.data?.detail||'This food item cannot be deleted while it is in an order.')}}
 const addCategory=async(e)=>{e.preventDefault();const categoryForm=e.currentTarget;const name=categoryForm.elements.categoryName.value.trim();if(!name)return;try{await api.post('/categories/',{name});categoryForm.reset();await load();setNotice(`Category ${name} added.`)}catch(err){setError(err.response?.data?.name?.[0]||'Could not add category.')}}
 return <><div className="page-head"><div><span className="eyebrow">Catalogue management</span><h1>Add and manage food</h1></div><span className="pill">Upload a real food photo</span></div>{notice&&<div className="notice manager-notice">{notice}</div>}{error&&<div className="error manager-notice">{error}</div>}<div className="manager-layout"><section className="panel"><h3>{editing?'Edit food item':'Add new food item'}</h3><form className="food-form" onSubmit={save}><label>Food name<input required maxLength={150} value={form.name} onChange={e=>setForm({...form,name:e.target.value})}/></label><label>Category<select required value={form.category} onChange={e=>setForm({...form,category:e.target.value})}><option value="">Select category</option>{categories.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></label><label>Description<textarea value={form.description} onChange={e=>setForm({...form,description:e.target.value})}/></label><div className="form-pair"><label>Price (₹)<input type="number" min="0.01" step="0.01" required value={form.price} onChange={e=>setForm({...form,price:e.target.value})}/></label><label>Offer price (₹)<input type="number" min="0" step="0.01" value={form.discounted_price} onChange={e=>setForm({...form,discounted_price:e.target.value})}/></label></div><div className="form-pair"><label>Stock quantity<input type="number" min="0" step="1" required value={form.stock} onChange={e=>setForm({...form,stock:e.target.value})}/></label><label>Prep time (minutes)<input type="number" min="1" required value={form.preparation_time} onChange={e=>setForm({...form,preparation_time:e.target.value})}/></label></div><label>Allergens<input placeholder="e.g. milk, nuts, gluten" value={form.allergens} onChange={e=>setForm({...form,allergens:e.target.value})}/></label><label className="photo-upload"><ImagePlus size={19}/><span>{photo?.name||'Choose food photo (JPG, PNG, max 5 MB)'}</span><input type="file" accept="image/jpeg,image/png,image/webp" onChange={e=>setPhoto(e.target.files?.[0]||null)}/></label>{photo&&<img className="photo-preview" src={URL.createObjectURL(photo)} alt="Selected food preview"/>}<div className="check-row"><label><input type="checkbox" checked={form.is_vegetarian} onChange={e=>setForm({...form,is_vegetarian:e.target.checked})}/> Vegetarian</label><label><input type="checkbox" checked={form.available} onChange={e=>setForm({...form,available:e.target.checked})}/> Available to order</label><label><input type="checkbox" checked={form.featured} onChange={e=>setForm({...form,featured:e.target.checked})}/> Featured</label></div><div className="form-actions"><button className="btn primary">{editing?'Save changes':'Add food item'}</button>{editing&&<button type="button" className="btn ghost" onClick={reset}><X size={15}/> Cancel edit</button>}</div></form></section><section className="panel"><h3>Categories</h3><form className="category-form" onSubmit={addCategory}><input name="categoryName" placeholder="New category name" required/><button className="btn primary">Add</button></form><div className="category-list">{categories.map(c=><span key={c.id}>{c.name}</span>)}</div><h3 className="list-heading">Menu items ({items.filter(item=>item.available).length} available · {items.length} total)</h3><div className="manage-list">{items.map(item=><div className={`manage-row${item.available?'':' unavailable-row'}`} key={item.id}><div className="manage-thumb">{item.image?<img src={item.image} alt=""/>:<UtensilsCrossed size={20}/>}</div><div className="manage-details"><strong>{item.name}{!item.available&&<span className="unavailable-label">Unavailable</span>}</strong><small>₹{item.effective_price} · {item.stock} in stock</small></div><button className="icon-btn small-icon" onClick={()=>edit(item)} title="Edit"><Pencil size={15}/></button><button className="icon-btn small-icon delete-icon" onClick={()=>remove(item)} title="Delete"><Trash2 size={15}/></button></div>)}</div></section></div></>;
}

function Protected({children,roles=[]}){
 const {user}=useAuth();
 if(!user)return <Login />;
 if(roles.length&&!roles.includes(user.role))return <div className="empty panel">You do not have permission to access this page.</div>;
 return children;
}

function App(){
 return <AuthProvider><BrowserRouter><Routes><Route path="*" element={<Layout><Routes><Route path="/" element={<Landing/>}/><Route path="/login" element={<Login/>}/><Route path="/register" element={<Register/>}/><Route path="/menu" element={<Protected><Menu/></Protected>}/><Route path="/cart" element={<Protected><Cart/></Protected>}/><Route path="/orders" element={<Protected><Orders/></Protected>}/><Route path="/payments" element={<Protected><PaymentHistory/></Protected>}/><Route path="/staff" element={<Protected roles={['STAFF','ADMIN']}><Staff/></Protected>}/><Route path="/admin" element={<Protected roles={['ADMIN']}><Admin/></Protected>}/><Route path="/admin/menu" element={<Protected roles={['ADMIN']}><FoodManager/></Protected>}/></Routes></Layout>}/></Routes></BrowserRouter></AuthProvider>;
}
createRoot(document.getElementById('root')).render(<App/>);
