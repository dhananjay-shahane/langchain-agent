#!/usr/bin/env python3
"""
MCP Tools Test Suite
Comprehensive testing of all MCP tools with real examples
"""
import os
import sys
import json
from pathlib import Path

# Add MCP tools to path
sys.path.append(str(Path(__file__).parent / "server" / "services" / "mcp-tools"))

from las_analyzer import analyze_las_file, list_las_files, validate_las_file
from log_plotter import create_gamma_ray_plot, create_porosity_plot, create_resistivity_plot  
from formation_analyzer import analyze_gamma_ray_lithology, analyze_porosity_quality, analyze_fluid_contacts
from email_processor import process_email_content, analyze_email_content, handle_email_attachments


def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")


def print_result(test_name, result):
    """Print test results in a formatted way"""
    print(f"\n{test_name}:")
    print("-" * (len(test_name) + 1))
    
    if isinstance(result, dict):
        if result.get('success'):
            print("✅ SUCCESS")
            for key, value in result.items():
                if key != 'success':
                    if isinstance(value, (dict, list)) and key in ['curves', 'files', 'lithology_zones']:
                        print(f"  {key}: {len(value)} items")
                        if len(value) <= 3:  # Show details for small lists
                            for item in value:
                                if isinstance(item, dict):
                                    print(f"    - {item}")
                                else:
                                    print(f"    - {item}")
                        else:
                            print(f"    (showing first 3 items)")
                            for item in value[:3]:
                                if isinstance(item, dict):
                                    print(f"    - {item}")
                                else:
                                    print(f"    - {item}")
                    else:
                        print(f"  {key}: {value}")
        else:
            print("❌ FAILED")
            print(f"  Error: {result.get('error', 'Unknown error')}")
    else:
        print(f"Result: {result}")


def test_las_file_analysis():
    """Test LAS file analysis functionality"""
    print_section("LAS FILE ANALYSIS TESTS")
    
    # Test 1: List available LAS files
    result = list_las_files()
    print_result("List Available LAS Files", result)
    
    # Get first available LAS file for testing
    las_filename = None
    if result.get('success') and result.get('files'):
        las_filename = result['files'][0]['filename']
        print(f"\n📁 Using LAS file for tests: {las_filename}")
    
    if las_filename:
        # Test 2: Analyze LAS file
        result = analyze_las_file(las_filename)
        print_result(f"Analyze LAS File: {las_filename}", result)
        
        # Test 3: Validate LAS file
        result = validate_las_file(las_filename)
        print_result(f"Validate LAS File: {las_filename}", result)
    else:
        print("⚠️ No LAS files found - skipping analysis tests")


def test_log_plotting():
    """Test log plotting functionality"""
    print_section("LOG PLOTTING TESTS")
    
    # Get first available LAS file
    files_result = list_las_files()
    if not files_result.get('success') or not files_result.get('files'):
        print("⚠️ No LAS files found - skipping plotting tests")
        return
    
    las_filename = files_result['files'][0]['filename']
    print(f"\n📊 Creating plots for: {las_filename}")
    
    # Test 1: Create gamma ray plot
    result = create_gamma_ray_plot(las_filename)
    print_result("Create Gamma Ray Plot", result)
    
    # Test 2: Create porosity plot
    result = create_porosity_plot(las_filename)
    print_result("Create Porosity Plot", result)
    
    # Test 3: Create resistivity plot
    result = create_resistivity_plot(las_filename)
    print_result("Create Resistivity Plot", result)


def test_formation_analysis():
    """Test formation analysis functionality"""
    print_section("FORMATION ANALYSIS TESTS")
    
    # Get first available LAS file
    files_result = list_las_files()
    if not files_result.get('success') or not files_result.get('files'):
        print("⚠️ No LAS files found - skipping formation analysis tests")
        return
    
    las_filename = files_result['files'][0]['filename']
    print(f"\n🔬 Analyzing formation data for: {las_filename}")
    
    # Test 1: Analyze gamma ray lithology
    result = analyze_gamma_ray_lithology(las_filename)
    print_result("Gamma Ray Lithology Analysis", result)
    
    # Test 2: Analyze porosity quality
    result = analyze_porosity_quality(las_filename)
    print_result("Porosity Quality Analysis", result)
    
    # Test 3: Analyze fluid contacts
    result = analyze_fluid_contacts(las_filename)
    print_result("Fluid Contacts Analysis", result)


def test_email_processing():
    """Test email processing functionality"""
    print_section("EMAIL PROCESSING TESTS")
    
    # Test data
    test_emails = [
        {
            'sender': 'john.smith@oilcompany.com',
            'subject': 'Urgent: LAS File Analysis Needed',
            'body': '''Hello,
            
We have an urgent request for analysis of our latest well log data. The drilling team encountered some unexpected formations and we need immediate interpretation of the gamma ray and porosity logs.

Please find the LAS file attached. We need this analysis ASAP for completion decisions.

Thanks,
John Smith
Senior Geologist
'''
        },
        {
            'sender': 'sarah.johnson@energycorp.com', 
            'subject': 'Question about resistivity interpretation',
            'body': '''Hi there,

I hope this email finds you well. I have a question about interpreting resistivity logs in carbonate formations.

In the LAS file I'm working with, I'm seeing some unusual resistivity spikes at around 2800-2900 ft. Could this indicate hydrocarbon presence or might it be related to formation water salinity?

Any guidance would be appreciated.

Best regards,
Sarah Johnson
Petrophysicist
Phone: 555-123-4567
'''
        },
        {
            'sender': 'complaints@drillingco.com',
            'subject': 'Issue with previous analysis report',
            'body': '''Dear Support Team,

I'm writing to express my disappointment with the recent formation analysis report we received. Several key parameters were missing and the gamma ray interpretation seems inconsistent with our geological model.

This has caused delays in our drilling program and we need this resolved immediately.

Please contact me to discuss this issue.

Regards,
Mike Wilson
Operations Manager
'''
        }
    ]
    
    for i, test_email in enumerate(test_emails, 1):
        print(f"\n📧 Processing Test Email {i}")
        result = process_email_content(
            test_email['subject'],
            test_email['body'], 
            test_email['sender']
        )
        print_result(f"Email Processing - Test {i}", result)


def test_attachment_handling():
    """Test email attachment handling"""
    print_section("EMAIL ATTACHMENT HANDLING TESTS")
    
    # Check for existing attachments in the email attachments directory
    attachments_dir = Path("data/email-attachments")
    if attachments_dir.exists():
        attachment_files = list(attachments_dir.glob("*"))
        if attachment_files:
            attachment_names = [f.name for f in attachment_files]
            print(f"📎 Found {len(attachment_names)} attachments to test with")
            
            result = handle_email_attachments(attachment_names)
            print_result("Handle Email Attachments", result)
        else:
            print("⚠️ No attachments found in data/email-attachments - creating test scenario")
            # Create a mock attachment result
            mock_result = {
                'message': 'No attachments found in email-attachments directory',
                'suggestion': 'Place LAS files in data/email-attachments/ to test attachment handling',
                'attachment_count': 0
            }
            print_result("Handle Email Attachments", mock_result)
    else:
        print("⚠️ Email attachments directory not found")


def test_integrated_workflow():
    """Test an integrated workflow combining multiple tools"""
    print_section("INTEGRATED WORKFLOW TEST")
    
    print("\n🔄 Running integrated workflow: Email to Analysis Pipeline")
    
    # Step 1: Process an email with LAS file request
    email_result = process_email_content(
        "LAS Analysis Request - Well A-123",
        "Please analyze the attached LAS file for porosity and gamma ray interpretation. We need formation tops identification.",
        "geologist@oilfield.com"
    )
    
    print_result("Step 1: Process Email Request", email_result)
    
    # Step 2: List available LAS files (simulating file availability)
    files_result = list_las_files()
    print_result("Step 2: Check Available LAS Files", files_result)
    
    if files_result.get('success') and files_result.get('files'):
        las_filename = files_result['files'][0]['filename']
        
        # Step 3: Perform requested analysis
        print(f"\n📊 Performing requested analysis on: {las_filename}")
        
        # Analyze gamma ray (as requested in email)
        gamma_result = analyze_gamma_ray_lithology(las_filename)
        print_result("Step 3a: Gamma Ray Analysis", gamma_result)
        
        # Analyze porosity (as requested in email)
        porosity_result = analyze_porosity_quality(las_filename)
        print_result("Step 3b: Porosity Analysis", porosity_result)
        
        # Create visualizations
        plot_result = create_gamma_ray_plot(las_filename)
        print_result("Step 4: Generate Gamma Ray Plot", plot_result)
        
        # Step 5: Generate summary response
        if gamma_result.get('success') and porosity_result.get('success'):
            summary = {
                'success': True,
                'analysis_completed': True,
                'las_file_analyzed': las_filename,
                'gamma_ray_zones': len(gamma_result.get('lithology_zones', [])),
                'porosity_zones': len(porosity_result.get('porosity_zones', [])),
                'plot_generated': plot_result.get('success', False),
                'output_file': plot_result.get('output_file'),
                'workflow_status': 'Completed successfully'
            }
            print_result("Step 5: Workflow Summary", summary)
        else:
            print("⚠️ Analysis step failed - workflow incomplete")


def run_all_tests():
    """Run all MCP tool tests"""
    print("🚀 Starting MCP Tools Comprehensive Test Suite")
    print(f"📅 Test run: {os.popen('date').read().strip()}")
    
    try:
        # Test each module
        test_las_file_analysis()
        test_log_plotting()
        test_formation_analysis()
        test_email_processing()
        test_attachment_handling()
        test_integrated_workflow()
        
        print_section("TEST SUITE COMPLETED")
        print("✅ All tests have been executed")
        print("\n📊 Test Summary:")
        print("- LAS file analysis tools: Tested")
        print("- Log plotting tools: Tested") 
        print("- Formation analysis tools: Tested")
        print("- Email processing tools: Tested")
        print("- Attachment handling: Tested")
        print("- Integrated workflow: Tested")
        
        print("\n💡 Usage Examples:")
        print("1. To analyze a specific LAS file:")
        print("   python -c \"from las_analyzer import analyze_las_file; print(analyze_las_file('your_file.las'))\"")
        print("\n2. To create a gamma ray plot:")
        print("   python -c \"from log_plotter import create_gamma_ray_plot; print(create_gamma_ray_plot('your_file.las'))\"")
        print("\n3. To process an email:")
        print("   python -c \"from email_processor import process_email_content; print(process_email_content('Subject', 'Body', 'email@example.com'))\"")
        
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()