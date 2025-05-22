import React, { useState } from "react";

export default function ProductForm({ onSubmit }) {
  const [url, setUrl] = useState("");
  const [email, setEmail] = useState("");
  const [targetPrice, setTargetPrice] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!url) return;
    onSubmit({ url, email, targetPrice });
    setUrl("");
    setEmail("");
    setTargetPrice("");
  };

  return (
    <form onSubmit={handleSubmit} className="bg-white p-4 rounded shadow space-y-2">
      <input
        type="url"
        placeholder="Amazon Product URL"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        className="input input-bordered w-full"
        required
      />
      <div className="flex gap-2">
        <input
          type="email"
          placeholder="Your Email (for alerts)"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="input input-bordered flex-1"
        />
        <input
          type="number"
          placeholder="Target Price (₹)"
          value={targetPrice}
          onChange={(e) => setTargetPrice(e.target.value)}
          className="input input-bordered flex-1"
        />
      </div>
      <button type="submit" className="btn btn-primary w-full">Track Product</button>
    </form>
  );
}
