import React from "react";

export default function ProductCard({ product }) {
  if (!product) return null;
  return (
    <div className="bg-white rounded shadow p-4 flex items-center gap-4">
      <img src={product.image_url} alt={product.name} className="w-20 h-20 object-contain" />
      <div>
        <h2 className="font-semibold text-lg">{product.name}</h2>
        <p className="text-gray-700">Current Price: <span className="font-bold">₹{product.current_price}</span></p>
        <a href={product.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 underline text-sm">View on {product.platform}</a>
      </div>
    </div>
  );
}
