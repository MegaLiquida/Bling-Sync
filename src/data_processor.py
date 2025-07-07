
import pandas as pd

def read_excel_data(file_path):
    df = pd.read_excel(file_path)
    return df

def write_excel_data(df, output_path):
    df.to_excel(output_path, index=False)

def process_products(df, api_client, access_token):
    df["EAN_Found"] = None
    df["Search_Status"] = "Not Processed"

    for index, row in df.iterrows():
        product_description = row["Item name"] # Assumindo que a coluna de descrição se chama "Item name"
        print(f"Searching EAN for: {product_description}")

        try:
            search_results = api_client.search_product(product_description, access_token)
            if search_results and search_results["results"]:
                # Pega o primeiro resultado da busca
                item_id = search_results["results"][0]["id"]
                item_details = api_client.get_item_details(item_id, access_token)

                ean = None
                if "attributes" in item_details:
                    for attr in item_details["attributes"]:
                        if attr["id"] == "GTIN" or attr["id"] == "EAN":
                            ean = attr["value_name"]
                            break
                
                if ean:
                    df.loc[index, "EAN_Found"] = ean
                    df.loc[index, "Search_Status"] = "Found"
                    print(f"EAN found for {product_description}: {ean}")
                else:
                    df.loc[index, "Search_Status"] = "EAN Not Found in Details"
                    print(f"EAN not found in details for {product_description}")
            else:
                df.loc[index, "Search_Status"] = "Product Not Found"
                print(f"Product not found for {product_description}")

        except Exception as e:
            df.loc[index, "Search_Status"] = f"Error: {e}"
            print(f"Error processing {product_description}: {e}")

    return df


