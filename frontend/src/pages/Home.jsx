import React, { useState } from "react";
import Header from "../components/Header";
import ProductForm from "../components/ProductForm";
import ProductCard from "../components/ProductCard";
import PriceHistoryChart from "../components/PriceHistoryChart";
import ComparisonTable from "../components/ComparisonTable";
import AlertForm from "../components/AlertForm";
import AlertStatus from "../components/AlertStatus";
import {
  trackProduct,
  getPriceHistory,
  getComparisons,
  setAlert,
} from "../services/api";

export default function Home() {
  const [product, setProduct] = useState(null);
  const [history, setHistory] = useState([]);
  const [comparisons, setComparisons] = useState([]);
  const [alertStatus, setAlertStatus] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleTrackProduct = async ({ url, email, targetPrice }) => {
    setLoading(true);
    setAlertStatus(null);
    try {
      // Track product and get product details
      const { data: prod } = await trackProduct({ url });
      setProduct(prod);

      // Fetch price history
      const { data: hist } = await getPriceHistory(prod.product_id);
      setHistory(hist);

      // Fetch comparison data (bonus)
      try {
        const { data: comp } = await getComparisons(prod.product_id);
        setComparisons(comp);
      } catch {
        setComparisons([]);
      }

      // If user provided alert info, set alert
      if (email && targetPrice) {
        await setAlert({
          product_id: prod.product_id,
          email,
          target_price: Number(targetPrice),
        });
        setAlertStatus("scheduled");
      }
    } catch (err) {
      alert("Failed to track product. Please check the URL and try again.");
      setProduct(null);
      setHistory([]);
      setComparisons([]);
    }
    setLoading(false);
  };

  return (
    <div>
      <Header />
      <main className="max-w-xl mx-auto mt-6 p-2">
        <ProductForm onSubmit={handleTrackProduct} />
        {loading && <div className="text-center p-4">Loading...</div>}
        {product && <ProductCard product={product} />}
        {history.length > 0 && <PriceHistoryChart history={history} />}
        {comparisons.length > 0 && <ComparisonTable comparisons={comparisons} />}
        {product && <AlertForm onSetAlert={async ({ email, targetPrice }) => {
          await setAlert({
            product_id: product.product_id,
            email,
            target_price: Number(targetPrice),
          });
          setAlertStatus("scheduled");
        }} />}
        <AlertStatus status={alertStatus} />
      </main>
    </div>
  );
}
