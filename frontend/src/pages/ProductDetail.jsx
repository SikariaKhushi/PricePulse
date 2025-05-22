import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import Header from "../components/Header";
import ProductCard from "../components/ProductCard";
import PriceHistoryChart from "../components/PriceHistoryChart";
import ComparisonTable from "../components/ComparisonTable";
import AlertForm from "../components/AlertForm";
import AlertStatus from "../components/AlertStatus";
import {
  getProduct,
  getPriceHistory,
  getComparisons,
  setAlert,
} from "../services/api";

export default function ProductDetail() {
  const { id } = useParams();
  const [product, setProduct] = useState(null);
  const [history, setHistory] = useState([]);
  const [comparisons, setComparisons] = useState([]);
  const [alertStatus, setAlertStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      try {
        const { data: prod } = await getProduct(id);
        setProduct(prod);
        const { data: hist } = await getPriceHistory(id);
        setHistory(hist);
        try {
          const { data: comp } = await getComparisons(id);
          setComparisons(comp);
        } catch {
          setComparisons([]);
        }
      } catch {
        setProduct(null);
        setHistory([]);
        setComparisons([]);
      }
      setLoading(false);
    }
    fetchData();
  }, [id]);

  const handleSetAlert = async ({ email, targetPrice }) => {
    await setAlert({
      product_id: id,
      email,
      target_price: Number(targetPrice),
    });
    setAlertStatus("scheduled");
  };

  return (
    <div>
      <Header />
      <main className="max-w-xl mx-auto mt-6 p-2">
        {loading && <div className="text-center p-4">Loading...</div>}
        {product && <ProductCard product={product} />}
        {history.length > 0 && <PriceHistoryChart history={history} />}
        {comparisons.length > 0 && <ComparisonTable comparisons={comparisons} />}
        {product && <AlertForm onSetAlert={handleSetAlert} />}
        <AlertStatus status={alertStatus} />
      </main>
    </div>
  );
}
