import React, { useEffect, useRef, useState } from 'react';
import { ArrowRight, Check, CircleAlert, CreditCard, Landmark, LoaderCircle, Receipt, ShieldCheck, Smartphone, Wallet, X } from 'lucide-react';
import { api, fetchAll } from './api';
import gcletLogo from './assets/gclet-college-logo.jpg';
import './payment-flow.css';

const money = (value) => new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  minimumFractionDigits: 2,
}).format(Number(value || 0));

const methods = [
  { id: 'UPI', label: 'UPI', note: 'Dummy UPI ID', Icon: Smartphone },
  { id: 'CARD', label: 'Card', note: 'Test card only', Icon: CreditCard },
  { id: 'NETBANKING', label: 'Net banking', note: 'Demo bank', Icon: Landmark },
  { id: 'WALLET', label: 'Wallet', note: 'Demo wallet', Icon: Wallet },
];

export function DemoPaymentModal({ order, onClose, onPaymentComplete }) {
  const [method, setMethod] = useState('UPI');
  const [phase, setPhase] = useState('ready');
  const [upiId, setUpiId] = useState('');
  const [cardNumber, setCardNumber] = useState('');
  const [expiry, setExpiry] = useState('');
  const [cvv, setCvv] = useState('');
  const [bank, setBank] = useState('');
  const [wallet, setWallet] = useState('');
  const [simulatedResult, setSimulatedResult] = useState('SUCCESS');
  const [attempt, setAttempt] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const idempotencyKey = useRef(null);
  const busyRef = useRef(false);

  useEffect(() => {
    if (phase !== 'success') return undefined;
    const timer = window.setTimeout(onPaymentComplete, 2000);
    return () => window.clearTimeout(timer);
  }, [phase, onPaymentComplete]);

  const validateDemoMethod = () => {
    if (method === 'UPI' && !/^[a-zA-Z0-9._-]+@demo$/.test(upiId.trim())) {
      return 'Enter a dummy UPI ID ending in @demo, such as student@demo.';
    }
    if (method === 'CARD') {
      if (cardNumber.replace(/\s/g, '') !== '4242424242424242' || !/^\d{2}\/\d{2}$/.test(expiry) || cvv !== '123') {
        return 'Use only the displayed demo card number, expiry 12/30, and CVV 123.';
      }
    }
    if (method === 'NETBANKING' && !bank) return 'Choose a demo bank to continue.';
    if (method === 'WALLET' && !wallet) return 'Choose a demo wallet to continue.';
    return '';
  };

  const payNow = async () => {
    if (busyRef.current) return;
    const validationError = validateDemoMethod();
    if (validationError) {
      setError(validationError);
      return;
    }
    busyRef.current = true;
    setBusy(true);
    setError('');
    setPhase('processing');
    let completed = false;
    try {
      if (!idempotencyKey.current) idempotencyKey.current = window.crypto.randomUUID();
      const { data: startedAttempt } = await api.post('/payments/create-demo-payment/', {
        order_id: order.id,
        method,
        idempotency_key: idempotencyKey.current,
      });
      setAttempt(startedAttempt);
      await new Promise((resolve) => window.setTimeout(resolve, 1250));
      const { data: result } = await api.post('/payments/verify-demo-payment/', {
        attempt_id: startedAttempt.id,
        simulated_result: simulatedResult,
      });
      setAttempt(result.attempt);
      completed = ['SUCCESS', 'FAILED', 'CANCELLED'].includes(result.attempt.status);
      if (result.attempt.status === 'SUCCESS') {
        setPhase('success');
      } else {
        setError(result.attempt.result_message || 'The simulated payment could not be completed.');
        setPhase('failure');
      }
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'The simulated payment could not be verified. You can safely retry this order.');
      setPhase('failure');
    } finally {
      if (completed) idempotencyKey.current = null;
      busyRef.current = false;
      setBusy(false);
    }
  };

  const retry = () => {
    setError('');
    setAttempt(null);
    setPhase('ready');
    if (attempt?.status === 'FAILED' || attempt?.status === 'CANCELLED') idempotencyKey.current = null;
  };

  const close = () => {
    if (!busyRef.current) onClose();
  };

  return (
    <div className="payment-backdrop" onMouseDown={(event) => {
      if (event.target === event.currentTarget && phase !== 'processing') close();
    }}>
      <section className="payment-modal" role="dialog" aria-modal="true" aria-labelledby="payment-title">
        <header className="payment-modal-head">
          <div className="payment-brand">
            <img src={gcletLogo} alt="GCLET college emblem" />
            <div><strong>GCLET Smart Canteen</strong><span>Secure demo checkout</span></div>
          </div>
          <div className="payment-test-badge"><ShieldCheck size={14} /> SIMULATED PAYMENT - TEST MODE</div>
          <button className="payment-close" type="button" onClick={close} disabled={busy} aria-label="Close checkout"><X size={19} /></button>
        </header>

        {phase === 'processing' && (
          <div className="payment-state payment-processing" aria-live="polite">
            <div className="payment-orbit"><span className="payment-coin">₹</span><LoaderCircle size={74} /></div>
            <span className="payment-state-label">TEST MODE · NO MONEY WILL BE CHARGED</span>
            <h2 id="payment-title">Verifying your simulated payment</h2>
            <p>Securely checking the demo transaction for order <strong>{order.number}</strong>.</p>
            <div className="processing-steps"><span className="complete-step">Order confirmed</span><i /><span>Payment verification</span><i /><span>Receipt ready</span></div>
          </div>
        )}

        {phase === 'success' && (
          <div className="payment-state payment-success" aria-live="polite">
            <div className="payment-success-icon"><Check size={38} strokeWidth={3} /></div>
            <span className="payment-state-label">SIMULATED PAYMENT - TEST MODE</span>
            <h2 id="payment-title">Payment Verified Successfully!</h2>
            <p>Your order has been placed successfully!</p>
            <div className="payment-result-details">
              <span>Transaction ID<strong>{attempt?.transaction_id}</strong></span>
              <span>Order ID<strong>{order.number}</strong></span>
              <span>Amount paid<strong>{money(attempt?.amount)}</strong></span>
            </div>
            <small className="payment-redirect-note">Taking you to order tracking…</small>
          </div>
        )}

        {phase === 'failure' && (
          <div className="payment-state payment-failure" aria-live="polite">
            <div className="payment-failure-icon"><CircleAlert size={38} /></div>
            <span className="payment-state-label">SIMULATED PAYMENT - TEST MODE</span>
            <h2 id="payment-title">Payment not completed</h2>
            <p>{error}</p>
            <div className="payment-failure-order">Order <strong>{order.number}</strong> is saved. No duplicate order was created and no money was charged.</div>
            <div className="payment-failure-actions">
              <button className="btn primary" type="button" onClick={retry}>Retry payment <ArrowRight size={16} /></button>
              <button className="btn ghost" type="button" onClick={close}>Close checkout</button>
            </div>
          </div>
        )}

        {phase === 'ready' && (
          <div className="payment-modal-body">
            <div className="payment-main">
              <div className="payment-heading">
                <div><span className="eyebrow">GCLET checkout</span><h2 id="payment-title">Complete your order</h2></div>
                <span className="payment-order-chip">Order {order.number}</span>
              </div>
              <div className="payment-methods" role="tablist" aria-label="Simulated payment method">
                {methods.map(({ id, label, note, Icon }) => (
                  <button className={`payment-method${method === id ? ' selected' : ''}`} type="button" role="tab" aria-selected={method === id} key={id} onClick={() => { setMethod(id); setError(''); }}>
                    <Icon size={19} /><strong>{label}</strong><small>{note}</small>
                  </button>
                ))}
              </div>

              {method === 'UPI' && (
                <label className="payment-input-label">Dummy UPI ID
                  <input value={upiId} onChange={(event) => setUpiId(event.target.value)} placeholder="student@demo" autoComplete="off" />
                  <small>Use an @demo ID only. This value stays in your browser and is never sent or stored.</small>
                </label>
              )}
              {method === 'CARD' && (
                <div className="payment-card-fields">
                  <div className="payment-safe-note"><ShieldCheck size={16} /> Test-only card form. Details stay in this browser and are never sent or stored.</div>
                  <label className="payment-input-label">Demo card number
                    <input inputMode="numeric" autoComplete="off" value={cardNumber} onChange={(event) => setCardNumber(event.target.value)} placeholder="4242 4242 4242 4242" />
                  </label>
                  <div className="payment-field-pair">
                    <label className="payment-input-label">Expiry<input autoComplete="off" value={expiry} onChange={(event) => setExpiry(event.target.value)} placeholder="12/30" /></label>
                    <label className="payment-input-label">CVV<input inputMode="numeric" autoComplete="off" value={cvv} onChange={(event) => setCvv(event.target.value)} placeholder="123" /></label>
                  </div>
                  <small className="payment-demo-card">Use demo values only: 4242 4242 4242 4242 · 12/30 · 123</small>
                </div>
              )}
              {method === 'NETBANKING' && (
                <label className="payment-input-label">Choose a demo bank
                  <select value={bank} onChange={(event) => setBank(event.target.value)}>
                    <option value="">Select a bank</option><option value="SBI DEMO">SBI Demo Bank</option><option value="HDFC DEMO">HDFC Demo Bank</option><option value="ICICI DEMO">ICICI Demo Bank</option>
                  </select>
                </label>
              )}
              {method === 'WALLET' && (
                <label className="payment-input-label">Choose a demo wallet
                  <select value={wallet} onChange={(event) => setWallet(event.target.value)}>
                    <option value="">Select a wallet</option><option value="CAMPUS WALLET">Campus Demo Wallet</option><option value="GCLET WALLET">GCLET Demo Wallet</option>
                  </select>
                </label>
              )}

              <div className="payment-scenario">
                <div><strong>Demo outcome</strong><small>Choose a simulated result for your project demonstration.</small></div>
                <div className="payment-scenario-options">
                  <button type="button" className={simulatedResult === 'SUCCESS' ? 'active' : ''} onClick={() => setSimulatedResult('SUCCESS')}>Success</button>
                  <button type="button" className={simulatedResult === 'FAILED' ? 'active' : ''} onClick={() => setSimulatedResult('FAILED')}>Failure</button>
                </div>
              </div>
              {error && <div className="payment-inline-error" role="alert">{error}</div>}
              <div className="payment-disclaimer"><ShieldCheck size={16} /><span>This is a simulation only. No bank, wallet, or payment gateway is contacted.</span></div>
              <button className="btn primary payment-pay-button" type="button" onClick={payNow} disabled={busy}>
                Pay {money(order.total)} <ArrowRight size={17} />
              </button>
            </div>

            <aside className="payment-order-panel">
              <span className="payment-panel-overline">ORDER SUMMARY</span>
              <h3>Your canteen order</h3>
              <div className="payment-order-items">
                {order.items.map((item) => (
                  <div className="payment-order-item" key={item.id}>
                    <span><strong>{item.name}</strong><small>Qty {item.quantity} × {money(item.unit_price)}</small></span>
                    <b>{money(item.line_total)}</b>
                  </div>
                ))}
              </div>
              <div className="payment-order-totals">
                <div><span>Subtotal</span><b>{money(order.subtotal)}</b></div>
                {Number(order.discount) > 0 && <div><span>Discount</span><b>−{money(order.discount)}</b></div>}
                <div><span>Tax</span><b>{money(order.tax)}</b></div>
                <div className="payment-final-total"><span>Total payable</span><strong>{money(order.total)}</strong></div>
              </div>
              <div className="payment-order-footnote"><ShieldCheck size={15} /> Final amount verified by the GCLET server.</div>
            </aside>
          </div>
        )}
      </section>
    </div>
  );
}

export function PaymentHistory({ compact = false }) {
  const [payments, setPayments] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(null);

  useEffect(() => {
    let active = true;
    fetchAll('/payments/history/').then((data) => {
      if (active) setPayments(data);
    }).catch(() => {
      if (active) setError('Could not load payment history. Please refresh and try again.');
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, []);

  const downloadReceipt = async (payment) => {
    setDownloading(payment.id);
    setError('');
    try {
      const response = await api.get(`/payments/${payment.id}/receipt/`, { responseType: 'blob' });
      const objectUrl = URL.createObjectURL(response.data);
      const link = document.createElement('a');
      link.href = objectUrl;
      link.download = `GCLET-${payment.order_number}-receipt.txt`;
      link.click();
      URL.revokeObjectURL(objectUrl);
    } catch {
      setError('Receipt is not available yet. It can be downloaded after successful payment.');
    } finally {
      setDownloading(null);
    }
  };

  const rows = payments.flatMap((payment) => {
    if (!payment.attempts?.length) {
      return [{ payment, attempt: null, key: `payment-${payment.id}` }];
    }
    return payment.attempts.map((attempt) => ({
      payment,
      attempt,
      key: `attempt-${attempt.id}`,
    }));
  });

  return (
    <section className={`payment-history${compact ? ' compact' : ''}`}>
      {!compact && <div className="page-head"><div><span className="eyebrow">Account</span><h1>Payment history</h1></div></div>}
      {error && <div className="payment-inline-error" role="alert">{error}</div>}
      {loading ? <div className="empty panel">Loading payment history…</div> : rows.length ? (
        <div className="payment-history-table-wrap">
          <table className="payment-history-table">
            <thead><tr><th>Transaction</th><th>Order</th><th>Method</th><th>Amount</th><th>Date</th><th>Status</th><th>Receipt</th></tr></thead>
            <tbody>{rows.map(({ payment, attempt, key }) => {
              const status = attempt?.status || payment.status;
              const transactionId = attempt?.transaction_id || payment.transaction_id || '—';
              const amount = attempt?.amount || payment.amount;
              const method = attempt?.method || payment.method;
              const createdAt = attempt?.created_at || payment.paid_at || payment.created_at;
              const receiptAvailable = payment.status === 'PAID' && payment.transaction_id === transactionId;
              return (
                <tr key={key}>
                  <td className="payment-transaction-id">{transactionId}</td>
                  <td>{payment.order_number}</td>
                  <td>{method.replace('_', ' ')}</td>
                  <td>{money(amount)}</td>
                  <td>{new Date(createdAt).toLocaleString('en-IN')}</td>
                  <td><span className={`payment-status-pill ${status.toLowerCase()}`}>{status}</span></td>
                  <td>{receiptAvailable ? <button className="payment-receipt-button" type="button" onClick={() => downloadReceipt(payment)} disabled={downloading === payment.id}><Receipt size={15} /> {downloading === payment.id ? 'Saving…' : 'Download'}</button> : '—'}</td>
                </tr>
              );
            })}</tbody>
          </table>
        </div>
      ) : !error ? <div className="empty panel">No payment transactions yet.</div> : null}
      <p className="payment-history-note"><ShieldCheck size={15} /> All GCLET online transactions shown here are simulated. No money was charged.</p>
    </section>
  );
}
