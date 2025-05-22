import React, { useState } from "react";

export default function AlertForm({ onSetAlert }) {
  const [email, setEmail] = useState("");
  const [targetPrice, setTargetPrice] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!email || !targetPrice) return;
    onSetAlert({ email, targetPrice });
    setEmail("");
    setTargetPrice("");
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-2 mt-4">
      <input
        type="email"
        placeholder="Your Email"
        value={email}
        onChange={e => setEmail(e.target.value)}
        className="input input-bordered"
        required
      />
      <input
        type="number"
        placeholder="Target Price"
        value={targetPrice}
        onChange={e => setTargetPrice(e.target.value)}
        className="input input-bordered"
        required
      />
      <button type="submit" className="btn btn-primary">Set Alert</button>
    </form>
  );
}
