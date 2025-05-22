import React from "react";

export default function Header() {
  return (
    <header className="bg-blue-600 text-white p-4 flex items-center justify-between">
      <h1 className="text-2xl font-bold">PricePulse</h1>
      <span className="text-sm">E-Commerce Price Tracker & Comparator</span>
    </header>
  );
}
